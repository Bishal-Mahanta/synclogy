import os
import requests
from PIL import Image
import pandas as pd
import re
import uuid
import json

# Define the output directory
OUTPUT_DIR = "output/images"

def safe_create_directory(path):
    """
    Safely creates a directory, handling potential errors.
    """
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception as e:
        print(f"Error creating directory {path}: {e}")
        return False

def sanitize_filename(filename, max_length=255):
    """
    Sanitize filename by:
    1. Removing invalid characters
    2. Replacing multiple spaces with a single space
    3. Truncating to max length
    4. Ensuring the filename is valid across different operating systems
    """
    # Remove invalid characters for all operating systems
    filename = re.sub(r'[\\/:*?"<>|]', '-', filename)
    
    # Replace multiple spaces with a single space
    filename = re.sub(r'\s+', ' ', filename)
    
    # Strip leading/trailing spaces
    filename = filename.strip()
    
    # Truncate to max length
    filename = filename[:max_length]
    
    # Ensure the filename is not empty
    if not filename:
        filename = "unnamed_file"
    
    return filename

def parse_image_urls(image_urls_str):
    """
    Attempt to parse image URLs using multiple methods.
    """
    if not image_urls_str or not isinstance(image_urls_str, str):
        return []
    
    # Try multiple parsing methods
    parsing_methods = [
        lambda x: eval(x),  # Python literal evaluation
        lambda x: json.loads(x),  # JSON parsing
        lambda x: [x] if isinstance(x, str) else []  # Treat as single URL if string
    ]
    
    for method in parsing_methods:
        try:
            urls = method(image_urls_str)
            # Validate that result is a list of strings
            if isinstance(urls, list) and all(isinstance(url, str) for url in urls):
                return urls
        except Exception as e:
            print(f"Parsing method failed: {e}")
    
    print(f"WARNING: Could not parse image URLs from: {image_urls_str}")
    return []

def extract_resolution_from_url(url):
    """
    Extracts the resolution from the URL based on specific patterns.
    Returns a tuple of (width, height) or (0, 0) if no resolution found.
    """
    try:
        # Match patterns like '416/416'
        match_full = re.search(r'(\d+)/(\d+)', url)
        if match_full:
            return (int(match_full.group(1)), int(match_full.group(2)))

        # Match patterns like 'SY355', 'SL1200', etc.
        match_suffix = re.search(r'[SXL]\w*(\d+)', url)
        if match_suffix:
            size = int(match_suffix.group(1))
            return (size, size)

        # Additional pattern for common e-commerce image URLs
        match_dims = re.search(r'(\d+)x(\d+)', url)
        if match_dims:
            return (int(match_dims.group(1)), int(match_dims.group(2)))

        return (0, 0)
    except Exception as e:
        print(f"Error extracting resolution from {url}: {e}")
        return (0, 0)

def is_high_resolution(url, min_width=900, min_height=900):
    """
    Check if the image resolution meets the minimum requirements.
    """
    width, height = extract_resolution_from_url(url)
    
    # Debug logging
    print(f"URL: {url}")
    print(f"Extracted resolution: {width}x{height}")
    print(f"Minimum required: {min_width}x{min_height}")
    
    return width >= min_width and height >= min_height

def download_image(url, save_path):
    """
    Download image with comprehensive error handling and convert to PNG.
    """
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        # Download image
        response = requests.get(url, stream=True, timeout=15)
        response.raise_for_status()
        
        # Save temporary file
        temp_path = save_path + "_temp"
        with open(temp_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        
        # Open and convert to PNG
        with Image.open(temp_path) as img:
            # Convert to RGB to handle different color modes
            rgb_img = img.convert('RGB')
            rgb_img.save(save_path, 'PNG')
        
        # Remove temporary file
        os.remove(temp_path)
        
        return save_path
    except requests.exceptions.RequestException as e:
        print(f"Network error downloading {url}: {e}")
    except IOError as e:
        print(f"File I/O error saving {save_path}: {e}")
    except Exception as e:
        print(f"Unexpected error downloading {url}: {e}")
    
    return None

def process_sheet(sheet_name, df):
    """
    Process a single sheet in the Excel file.
    """
    total_images_found = 0
    high_res_images_downloaded = 0

    for index, row in df.iterrows():
        try:
            # Extract product name
            product_name = str(row.get("Product Name", f"unknown_product_{index}")).strip()
            product_name = sanitize_filename(product_name)
            
            # Create product-specific directory
            product_dir = os.path.join(OUTPUT_DIR, product_name)
            safe_create_directory(product_dir)
            
            # Parse image URLs
            image_urls = row.get("Images", "[]")
            image_list = parse_image_urls(image_urls)
            
            print(f"\nProcessing Product: {product_name}")
            print(f"Found {len(image_list)} image URLs")
            
            # Download images
            for img_index, url in enumerate(image_list, start=1):
                total_images_found += 1
                
                # Check resolution
                # if is_high_resolution(url):
                # Generate unique filename
                unique_id = uuid.uuid4().hex[:8]
                width, height = extract_resolution_from_url(url)
                resolution_str = f"{width}x{height}"
                    
                # Always use .png extension
                filename = sanitize_filename(
                    f"{product_name}_original_{img_index:03d}_{resolution_str}_{unique_id}.png"
                )
                save_path = os.path.join(product_dir, filename)
                    
                # Download image
                result = download_image(url, save_path)
                if result:
                    print(f"Successfully saved: {result}")
                    high_res_images_downloaded += 1
                else:
                    print(f"Failed to download: {url}")
                # else:
                #     print(f"Skipping low-resolution image: {url}")
        
        except Exception as e:
            print(f"Error processing row {index}: {e}")
    
    # Print summary
    print(f"\nSheet {sheet_name} Summary:")
    print(f"Total images found: {total_images_found}")
    print(f"High-resolution images downloaded: {high_res_images_downloaded}")

def process_excel_file(file_path):
    """
    Processes an Excel file with multiple sheets.
    """
    try:
        # Ensure output directory exists
        safe_create_directory(OUTPUT_DIR)
        
        # Read Excel file
        excel_data = pd.ExcelFile(file_path)
        
        # Process each sheet
        for sheet_name in excel_data.sheet_names:
            print(f"\n--- Processing sheet: {sheet_name} ---")
            df = excel_data.parse(sheet_name)
            
            # Check for required columns
            if "Product Name" in df.columns and "Images" in df.columns:
                process_sheet(sheet_name, df)
            else:
                print(f"Skipping sheet {sheet_name}: Missing required columns")
    
    except Exception as e:
        print(f"Critical error processing file {file_path}: {e}")

if __name__ == "__main__":
    input_excel_file = "data/products.xlsx"  # Path to the input Excel file
    process_excel_file(input_excel_file)