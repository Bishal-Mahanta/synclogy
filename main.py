import os
import logging
import pandas as pd
from data.input_handler import load_input_data  # Updated import
from spec.flipkart_scraper import FlipkartScraper
from spec.amazon_scraper import AmazonScraper
from spec.tech_scraper import TechScraper
from media.image_scraper import process_excel_file
from media.image_uploader import main as upload_and_save_links
from media.image_styler_and_optimizer import process_images_in_directory

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def append_to_sheet(output_filepath, sheet_name, new_data):
    try:
        if os.path.exists(output_filepath):
            with pd.ExcelWriter(output_filepath, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                try:
                    existing_data = pd.read_excel(output_filepath, sheet_name=sheet_name)
                    combined_data = pd.concat([existing_data, new_data], ignore_index=True)
                    combined_data = combined_data.drop_duplicates(subset=['Product Name'], keep='last')
                except ValueError:  # Sheet does not exist
                    combined_data = new_data

                combined_data.to_excel(writer, index=False, sheet_name=sheet_name)
                logging.info(f"Updated data written to sheet: {sheet_name}")
        else:
            with pd.ExcelWriter(output_filepath, engine='openpyxl', mode='w') as writer:
                new_data.to_excel(writer, index=False, sheet_name=sheet_name)
                logging.info(f"Created new sheet: {sheet_name}")
    except Exception as e:
        logging.error(f"Failed to write data to {sheet_name}: {e}")

def process_flipkart_products(input_filepath, output_filepath):
    product_df = pd.read_excel(input_filepath)  # Directly load data without validation
    if product_df.empty:
        logging.error("Input file is empty or invalid. Please check the file and try again.")
        return

    valid_products = []
    for _, row in product_df.iterrows():
        category = row['Category'].lower()
        valid_products.append(row)

    if not valid_products:
        logging.info("No valid products found in the input file.")
        return

    valid_product_df = pd.DataFrame(valid_products)
    not_found_products = []

    if not valid_product_df.empty:
        flipkart_scraper = FlipkartScraper()

        for _, product in valid_product_df.iterrows():
            product_name = product['Product Name']
            link = product.get('Link')  # Check for direct link
            model_name = product['Model Name']
            product_color = product['Color']
            category = product['Category'].lower()

            # If a direct link is provided, use it directly
            if pd.notna(link) and 'flipkart' in link.lower():
                logging.info(f"Using direct link for product: {product_name}")
                try:
                    product_details = flipkart_scraper.extract_product_details(link)
                    additional_table_data = flipkart_scraper.extract_additional_table_data(link)
                    
                    if additional_table_data:
                        for table_entry in additional_table_data:
                            product_details[table_entry["Header"]] = table_entry["Data"]
                    
                    if product_details:
                        sheet_name = f"Flipkart {category.capitalize()} Details"
                        product_details_df = pd.DataFrame([product_details])
                        append_to_sheet(output_filepath, sheet_name, product_details_df)
                    continue
                except Exception as e:
                    logging.error(f"Error processing direct link for {product_name}: {e}")
            
            # If no direct link, proceed with search
            search_query = f"{product_name} {model_name} {product_color}".replace('nan', '')
            logging.info(f"Searching for product on Flipkart: {search_query}")
            product_links = flipkart_scraper.search_product(search_query)

            if not product_links:
                logging.warning(f"Product not found: {search_query}")
                not_found_products.append(product)
                continue

            for parsed_name, link in product_links:
                logging.info(f"Extracting details for: {parsed_name}")
                product_details = flipkart_scraper.extract_product_details(link)

                additional_table_data = flipkart_scraper.extract_additional_table_data(link)
                if additional_table_data:
                    for table_entry in additional_table_data:
                        product_details[table_entry["Header"]] = table_entry["Data"]

                if product_details:
                    sheet_name = f"Flipkart {category.capitalize()} Details"
                    product_details_df = pd.DataFrame([product_details])
                    append_to_sheet(output_filepath, sheet_name, product_details_df)

        flipkart_scraper.close()

    if not_found_products:
        not_found_df = pd.DataFrame(not_found_products)
        append_to_sheet(output_filepath, "To Be Checked Again", not_found_df)
        logging.info("Products not found on Flipkart saved to 'To Be Checked Again'.")

def process_amazon_and_91mobiles(input_filepath, output_filepath):
    if not os.path.exists(output_filepath):
        logging.error(f"Output file '{output_filepath}' not found.")
        return

    try:
        not_found_df = pd.read_excel(output_filepath, sheet_name="To Be Checked Again")
    except ValueError:
        logging.error("'To Be Checked Again' sheet not found.")
        return

    if not_found_df.empty:
        logging.info("No products to process.")
        return

    tech_scraper = TechScraper(headless_mode=False)
    amazon_scraper = AmazonScraper()
    amazon_details = []

    for _, product in not_found_df.iterrows():
        product_name = product['Product Name']
        link = product.get('Link')  # Check for direct Amazon link
        link_rel = product.get('91 Link')  # Check for 91mobiles link
        model_name = product.get('Model Name', '')
        category = product['Category']
        search_query = f"{product_name} {model_name}".strip()
        logging.info(f"Processing: {search_query}")

        # Process 91mobiles details first
        tech_details = {}
        if pd.notna(link_rel):
            logging.info(f"Using direct 91mobiles link: {link_rel}")
            try:
                tech_details = tech_scraper.extract_technical_details(link_rel)
            except Exception as e:
                logging.error(f"Error extracting details from 91mobiles link: {e}")
        else:
            # If no direct link, search for 91mobiles link
            tech_link = tech_scraper.search_product(search_query)
            if tech_link:
                logging.info(f"Found link on 91mobiles: {tech_link}")
                try:
                    tech_details = tech_scraper.extract_technical_details(tech_link)
                except Exception as e:
                    logging.error(f"Error extracting details from 91mobiles search: {e}")

        # Process Amazon details
        
        # If direct Amazon link is provided, use it directly
        if pd.notna(link):
            logging.info(f"Using direct Amazon link: {link}")
            try:
                general_details = amazon_scraper.extract_product_details(link)

                # Merge tech details if available
                if tech_details:
                    general_details.update(tech_details)

                amazon_details.append(general_details)
                continue
            except Exception as e:
                logging.error(f"Error extracting Amazon product details from direct link: {e}")

        # If no direct link, search for Amazon link
        product_links = amazon_scraper.search_product(search_query)
        if not product_links:
            logging.warning(f"No products found for: {search_query}")
            continue

        # Process the first matching Amazon link
        for link in product_links:
            try:
                general_details = amazon_scraper.extract_product_details(link)

                # Merge tech details if available
                if tech_details:
                    general_details.update(tech_details)

                amazon_details.append(general_details)
                break
            except Exception as e:
                logging.error(f"Error extracting Amazon product details: {e}")

    amazon_scraper.close()
    tech_scraper.close()

    if amazon_details:
        amazon_df = pd.DataFrame(amazon_details)
        append_to_sheet(output_filepath, f"Amazon {category.capitalize()} Details", amazon_df)
        logging.info("Amazon product details saved to 'Amazon Product Details'.")


def process_images():
    input_file = "data/output_scraper_results.xlsx"
    if os.path.exists(input_file):
        logging.info(f"Processing images from {input_file}")
        process_excel_file(input_file)
    else:
        logging.error(f"Input file '{input_file}' not found.")
        
def upload_images_and_update_links():
    """
    Call the uploader script to upload images to Cloudinary and save their public URLs.
    """
    try:
        from media.image_uploader import main as upload_and_save_links
        logging.info("Starting image upload and link update process.")
        upload_and_save_links()
        logging.info("Image upload and link update process completed successfully.")
    except Exception as e:
        logging.error(f"Error during image upload and link update: {e}")


def style_and_optimize_images():
    input_directory = "output/images"
    logging.info("Starting image styling and optimization...")
    process_images_in_directory(input_directory)
    logging.info("Image styling and optimization completed.")



if __name__ == "__main__":
    input_filepath = "data/product_data.xlsx"
    output_filepath = "data/output_scraper_results.xlsx"

    if not os.path.exists(input_filepath):
        logging.error(f"Input file '{input_filepath}' not found.")
    else:
        process_flipkart_products(input_filepath, output_filepath)
        process_amazon_and_91mobiles(input_filepath, output_filepath)
        
    process_images()
    style_and_optimize_images()  # Style and optimize images
    upload_images_and_update_links()
