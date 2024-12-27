import pandas as pd
import os
import logging
import re

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def normalize_product_name(name):
    """Normalize product name for consistent matching"""
    if pd.isna(name):
        return ""
    # Remove special characters and convert to lowercase
    normalized = re.sub(r'[^a-zA-Z0-9]', '', str(name).lower())
    return normalized

def map_images_to_sheets(output_filepath: str, image_links_filepath: str) -> bool:
    """
    Maps image links to products in all sheets except 'To Be Checked Again'
    
    Args:
        output_filepath: Path to the Excel file containing product sheets
        image_links_filepath: Path to the Excel file containing image links
    
    Returns:
        bool: True if mapping was successful, False otherwise
    """
    try:
        # Load image links
        image_links = pd.read_excel(image_links_filepath)
        logging.info(f"Loaded {len(image_links)} image links")

        # Load all sheets from output file
        excel_file = pd.ExcelFile(output_filepath)
        sheets_dict = {}

        # Process each sheet except 'To Be Checked Again'
        for sheet_name in excel_file.sheet_names:
            if sheet_name.lower() != 'to be checked again':
                sheet_data = pd.read_excel(output_filepath, sheet_name=sheet_name)
                if not sheet_data.empty:
                    sheets_dict[sheet_name] = sheet_data
                    logging.info(f"Loaded sheet: {sheet_name} with {len(sheet_data)} rows")

        # Track matching statistics
        total_products = 0
        matched_products = 0

        # Process each sheet
        for sheet_name, sheet_data in sheets_dict.items():
            logging.info(f"Processing sheet: {sheet_name}")
            
            # Add image columns if they don't exist
            if 'webp' not in sheet_data.columns:
                sheet_data['webp'] = ''
            if 'jpeg' not in sheet_data.columns:
                sheet_data['jpeg'] = ''

            # Process each product in the sheet
            total_products += len(sheet_data)
            for idx, row in sheet_data.iterrows():
                product_name = row.get('Product Name', '')
                if pd.isna(product_name):
                    continue

                normalized_product_name = normalize_product_name(product_name)
                product_matched = False
                
                # Find matching images
                for _, image_row in image_links.iterrows():
                    file_name = image_row['File Name']
                    image_product_name = normalize_product_name(file_name.split('_original')[0])
                    
                    # Check for match
                    if normalized_product_name in image_product_name or image_product_name in normalized_product_name:
                        extension = file_name.split('.')[-1].lower()
                        if extension == 'webp':
                            current_links = str(sheet_data.at[idx, 'webp'])
                            if image_row['URL'] not in current_links:
                                sheet_data.at[idx, 'webp'] = f"{current_links}; {image_row['URL']}" if current_links else image_row['URL']
                        elif extension == 'jpg':
                            current_links = str(sheet_data.at[idx, 'jpeg'])
                            if image_row['URL'] not in current_links:
                                sheet_data.at[idx, 'jpeg'] = f"{current_links}; {image_row['URL']}" if current_links else image_row['URL']
                        product_matched = True

                if product_matched:
                    matched_products += 1

            # Clean up any leading/trailing semicolons and spaces
            sheet_data['webp'] = sheet_data['webp'].str.strip('; ')
            sheet_data['jpeg'] = sheet_data['jpeg'].str.strip('; ')
            
            sheets_dict[sheet_name] = sheet_data

        # Save all updated sheets back to the file
        with pd.ExcelWriter(output_filepath, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            for sheet_name, sheet_data in sheets_dict.items():
                sheet_data.to_excel(writer, sheet_name=sheet_name, index=False)
                logging.info(f"Updated sheet saved: {sheet_name}")

        # Log matching statistics
        logging.info(f"Image mapping completed: {matched_products}/{total_products} products matched with images")
        return True

    except Exception as e:
        logging.error(f"Error in map_images_to_sheets: {e}")
        return False

if __name__ == "__main__":
    # Example usage
    output_filepath = "data/output_scraper_results.xlsx"
    image_links_filepath = "data/uploaded_image_links.xlsx"
    
    if os.path.exists(output_filepath) and os.path.exists(image_links_filepath):
        map_images_to_sheets(output_filepath, image_links_filepath)
    else:
        logging.error("Required files not found.")