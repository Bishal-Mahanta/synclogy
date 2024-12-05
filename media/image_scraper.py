import os
import requests
from PIL import Image
import pandas as pd
import re
import uuid

# Define the output directory
OUTPUT_DIR = "output/images"

def create_directory(path):
    """
    Creates a directory if it doesn't exist.
    """
    os.makedirs(path, exist_ok=True)

def download_and_convert_image(url, save_path):
    """
    Downloads an image from a URL and saves it as a WEBP file.
    """
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(save_path, "wb") as file:
                file.write(response.content)
            # Convert to WEBP format
            img = Image.open(save_path)
            webp_path = save_path.replace(".jpg", ".webp").replace(".jpeg", ".webp").replace(".png", ".webp")
            img.save(webp_path, "WEBP", quality=100)
            os.remove(save_path)  # Remove the original file after conversion
            return webp_path
        else:
            print(f"Failed to download {url}")
            return None
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return None

def extract_resolution_from_url(url):
    """
    Extracts the resolution from the URL based on specific patterns.
    - If the URL contains '416/416', the resolution is '416x416'.
    - If the URL contains '1664/1664', the resolution is '1664x1664'.
    - If the URL contains 'SY355', 'SL1200', or similar patterns, extract the numeric value and use it as the resolution.
    """
    # Match patterns like '416/416' or '1664/1664'
    match_full = re.search(r'(\d+)/\1', url)
    if match_full:
        resolution = f"{match_full.group(1)}x{match_full.group(1)}"
        return resolution

    # Match patterns like 'SY355', 'SL1200', etc.
    match_suffix = re.search(r'[SXL]\w*(\d+)', url)
    if match_suffix:
        resolution = f"{match_suffix.group(1)}x{match_suffix.group(1)}"
        return resolution

    # Default resolution if no pattern is found
    return "unknown"

def generate_unique_id():
    """
    Generates a unique alphanumeric identifier.
    """
    return uuid.uuid4().hex[:8]  # 8-character alphanumeric ID

def get_file_extension(url):
    """
    Extracts the file extension from the URL.
    """
    return os.path.splitext(url.split("?")[0])[-1]  # Extracts extension ignoring query parameters

def download_image(url, save_path):
    """
    Downloads an image from the URL and saves it to the specified path.
    """
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(save_path, "wb") as file:
                file.write(response.content)
            return save_path
        else:
            print(f"Failed to download {url}")
            return None
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return None

def process_sheet(sheet_name, df):
    """
    Processes a single sheet to download and save images.
    """
    for _, row in df.iterrows():
        # Ensure Product Name is a string and truncate to 50 characters
        product_name = row.get("Product Name", "")
        if not isinstance(product_name, str):
            product_name = str(product_name)  # Convert to string if not already
        product_name = product_name.replace("/", "-").replace("\\", "-").strip()
        product_name = product_name[:50]  # Limit folder name to 50 characters

        # Ensure Images column contains a valid list
        image_urls = row.get("Images", "[]")
        if not isinstance(image_urls, str):
            continue  # Skip rows where Images is not a string

        # Create product-specific directory
        product_dir = os.path.join(OUTPUT_DIR, product_name)
        os.makedirs(product_dir, exist_ok=True)

        # Download images
        try:
            image_list = eval(image_urls)  # Convert the string representation of list back to list
            if not isinstance(image_list, list):
                continue

            for index, url in enumerate(image_list, start=1):
                resolution = extract_resolution_from_url(url)  # Extract resolution from URL
                unique_id = generate_unique_id()  # Generate unique alphanumeric ID
                file_extension = get_file_extension(url)  # Get original file extension
                image_name = f"{product_name}_original_{index:03d}_{resolution}_{unique_id}{file_extension}"
                save_path = os.path.join(product_dir, image_name)

                # Download the image
                downloaded_path = download_image(url, save_path)
                if downloaded_path:
                    print(f"Saved: {downloaded_path}")
        except Exception as e:
            print(f"Error processing images for {product_name}: {e}")
            
            
def process_excel_file(file_path):
    """
    Processes an Excel file with multiple sheets.
    """
    try:
        excel_data = pd.ExcelFile(file_path)
        for sheet_name in excel_data.sheet_names:
            print(f"Processing sheet: {sheet_name}")
            df = excel_data.parse(sheet_name)
            if "Product Name" in df.columns and "Images" in df.columns:
                process_sheet(sheet_name, df)
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")

if __name__ == "__main__":
    input_excel_file = "data/products.xlsx"  # Path to the input Excel file
    create_directory(OUTPUT_DIR)
    process_excel_file(input_excel_file)
