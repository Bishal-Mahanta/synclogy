import pandas as pd
import logging
import re

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def check_phone_in_sheet_name(sheet_name):
    """
    Check if 'Phone' is present in the sheet name (case-insensitive).
    
    Args:
        sheet_name (str): Name of the sheet to check
        
    Returns:
        bool: True if 'Phone' is found in the sheet name, False otherwise
    """
    return 'phone' in sheet_name.lower()

def process_phone_sheets(output_filepath, result_filepath, image_links_filepath):
    """
    Process and merge phone-related sheets from multiple Excel files.
    
    Args:
        output_filepath (str): Path to the input Excel file containing phone data sheets
        result_filepath (str): Path where the merged result will be saved
        image_links_filepath (str): Path to the Excel file containing image links
    """
    try:
        # Load relevant sheets from the output file
        sheet_names = pd.ExcelFile(output_filepath).sheet_names
        
        # Filter sheets containing the word 'Phone' (case-insensitive)
        phone_sheets = [sheet for sheet in sheet_names if check_phone_in_sheet_name(sheet)]
        if not phone_sheets:
            logging.error("No sheets containing 'Phone' found.")
            return

        logging.info(f"Found {len(phone_sheets)} phone-related sheets: {', '.join(phone_sheets)}")
        combined_data = pd.DataFrame()

        # Process each phone sheet
        for sheet in phone_sheets:
            try:
                data = pd.read_excel(output_filepath, sheet_name=sheet)
                logging.info(f"Processing sheet '{sheet}' with {len(data)} rows")
                combined_data = pd.concat([combined_data, data], ignore_index=True)
            except Exception as e:
                logging.error(f"Error processing sheet {sheet}: {e}")

        # If no data was combined, exit early
        if combined_data.empty:
            logging.error("No valid data found in 'Phone' sheets.")
            return

        # Load image links
        try:
            image_links = pd.read_excel(image_links_filepath)
            logging.info(f"Loaded {len(image_links)} image links")
        except Exception as e:
            logging.error(f"Error loading image links: {e}")
            return

        # Define columns to directly copy
        direct_columns = [
            "Product Name", "Offer Price", "MRP", "Description", "Meta Title", "Meta Keywords",
            "Meta Description", "Unique", "Link", "RAM", "Operating System", "Resolution", "Height", "Width",
            "Weight", "Primary Camera Features", "Secondary Camera Features"
        ]

        # Define column mappings for merging
        column_mappings = {
            ("RAM", "Memory"): "RAM",
            ("Processor", "Processor Type"): "Processor",
            ("Rear Camera", "Primary Camera"): "Primary Camera",
            ("Front Camera", "Secondary Camera"): "Secondary Camera",
            ("Battery", "Battery Capacity"): "Battery Capacity",
            ("Display", "Display Size"): "Display Size",
            ("CPU", "Processor Core"): "Processor Core",
            ("Graphics", "GPU"): "GPU",
            ("Display Type", "Resolution Type"): "Resolution",
            ("Thickness", "Depth"): "Thickness",
            ("Color", "Colour(s)"): "Colors",
            ("Video Recording", "Video Recording Resolution"): "Video Recording Features",
            ("Internal Memory", "Internal Storage"): "Internal Storage",
            ("Network Support", "Supported Networks"): "Supported Networks",
            ("Wi-Fi", "Wi-Fi Version"): "Wi-Fi Version",
            ("Bluetooth", "Bluetooth Version"): "Bluetooth Version",
            ("GPS", "GPS Support"): "GPS",
            ("Other Sensors", "Sensors"): "Sensors"
        }

        # Initialize the final DataFrame with direct columns
        available_direct_columns = [col for col in direct_columns if col in combined_data.columns]
        logging.info(f"Processing {len(available_direct_columns)} direct columns")
        final_data = combined_data[available_direct_columns].copy()

        # Process merged columns
        for (col1, col2), output_col in column_mappings.items():
            if col1 in combined_data.columns or col2 in combined_data.columns:
                final_data[output_col] = combined_data.get(col1, pd.Series()).combine_first(combined_data.get(col2, pd.Series()))
                logging.info(f"Merged columns {col1}/{col2} into {output_col}")
            else:
                final_data[output_col] = pd.Series()
                logging.warning(f"Neither {col1} nor {col2} found in data")

        # Map image links to the final data
        final_data['webp'] = ''
        final_data['png'] = ''

        link_count = 0
        for _, row in image_links.iterrows():
            try:
                # Extract product name from filename by removing the technical suffix
                product_name_match = row['File Name'].split('_original')[0].strip()
                extension = row['File Name'].split('.')[-1].lower()
                
                logging.info(f"Processing image: {row['File Name']}")
                logging.info(f"Extracted product name: {product_name_match}")

                # Escape special regex characters in the product name
                escaped_product_name = re.escape(product_name_match)
                
                # First try exact matching
                exact_matches = final_data['Product Name'] == product_name_match
                if exact_matches.any():
                    matched_rows = exact_matches
                    logging.info(f"Found exact match for image: {product_name_match}")
                else:
                    # Try regex matching if exact match fails
                    matched_rows = final_data['Product Name'].str.contains(escaped_product_name, na=False, case=False, regex=True)
                    if matched_rows.any():
                        logging.info(f"Found partial match for image: {product_name_match}")
                    else:
                        logging.warning(f"No match found for image: {product_name_match}")
                        # Log the available product names for debugging
                        logging.debug("Available product names:")
                        for name in final_data['Product Name']:
                            logging.debug(f"  - {name}")
                        continue

                match_count = matched_rows.sum()
                if match_count > 0:
                    if extension == 'webp':
                        final_data.loc[matched_rows, 'webp'] += row['URL'] + '; '
                        link_count += match_count
                    elif extension == 'png':
                        final_data.loc[matched_rows, 'png'] += row['URL'] + '; '
                        link_count += match_count
                    logging.info(f"Added {extension} image link for {match_count} products")
                
            except Exception as e:
                logging.error(f"Error processing image {row['File Name']}: {e}")
                continue

        logging.info(f"Mapped {link_count} image links to products")

        # Clean up trailing semicolons
        final_data['webp'] = final_data['webp'].str.strip('; ')
        final_data['png'] = final_data['png'].str.strip('; ')

        # Save the final DataFrame to the result file
        with pd.ExcelWriter(result_filepath, engine="openpyxl") as writer:
            final_data.to_excel(writer, index=False, sheet_name="Merged Phone Details")

        logging.info(f"Successfully created final sheet in {result_filepath} with {len(final_data)} rows")
    except Exception as e:
        logging.error(f"An error occurred during processing: {e}")
        raise

if __name__ == "__main__":
    # Example usage
    output_filepath = "output/phone_data.xlsx"
    result_filepath = "output/final_phone_sheet.xlsx"
    image_links_filepath = "output/image_links.xlsx"

    try:
        process_phone_sheets(output_filepath, result_filepath, image_links_filepath)
    except Exception as e:
        logging.error(f"Script execution failed: {e}")