import os
import re
from PIL import Image

# Configuration
MAIN_RESOLUTION = (1664, 1664)  # Target image size (1664x1664)
TARGET_RESOLUTION = (1400, 1400)  # Target image size (1664x1664)
BACKGROUND_COLOR = (255, 255, 255)  # White background color
IMAGE_QUALITY = 75  # Compression quality for WEBP and JPG format

def create_directory(path):
    """Creates a directory if it doesn't exist."""
    os.makedirs(path, exist_ok=True)

def clean_filename(filename):
    """
    Cleans the filename by removing resolution patterns and keeping the identifier
    Example: transforms "image_006_1664x1664_17efce4a" to "image_006_17efce4a"
    """
    # Split the filename and extension
    base_name = os.path.splitext(filename)[0]
    
    # Use regex to match the pattern and clean it
    pattern = r'(.+?)_\d+x\d+(_[a-f0-9]+)$'
    match = re.match(pattern, base_name)
    
    if match:
        # Combine the parts before the resolution and the identifier
        return match.group(1) + match.group(2)
    return base_name

def resize_and_center_image(input_path, webp_output_path, jpg_output_path):
    """
    Resizes the image to 1500x1500 (if necessary) and centers it on a 1664x1664 white background.
    Saves the output as both WEBP and JPG files with cleaned filenames.
    """
    try:
        # Clean the output filenames
        webp_base = clean_filename(os.path.basename(webp_output_path))
        jpg_base = clean_filename(os.path.basename(jpg_output_path))
        
        # Update output paths with cleaned names
        webp_output_path = os.path.join(os.path.dirname(webp_output_path), f"{webp_base}.webp")
        jpg_output_path = os.path.join(os.path.dirname(jpg_output_path), f"{jpg_base}.jpg")

        # Open the image
        with Image.open(input_path).convert("RGB") as img:
            # Check if the image is already 1664x1664
            if img.size == MAIN_RESOLUTION:
                # Resize directly to TARGET_RESOLUTION
                img = img.resize(TARGET_RESOLUTION, Image.Resampling.LANCZOS)
                img.save(webp_output_path, "WEBP", quality=IMAGE_QUALITY)
                img.save(jpg_output_path, "JPEG", quality=IMAGE_QUALITY)
                print(f"Image resized and saved with cleaned filename as WEBP and JPG: {webp_output_path}, {jpg_output_path}")
                return

            # Resize to a maximum of 1000x1000
            max_inner_resolution = (1200, 1200)
            img.thumbnail(max_inner_resolution, Image.Resampling.LANCZOS)

            # Create a white background of TARGET_RESOLUTION
            background = Image.new("RGB", TARGET_RESOLUTION, BACKGROUND_COLOR)

            # Center the resized image onto the white background
            x_offset = (TARGET_RESOLUTION[0] - img.size[0]) // 2
            y_offset = (TARGET_RESOLUTION[1] - img.size[1]) // 2

            background.paste(img, (x_offset, y_offset))

            # Save the final image as WEBP and JPG with cleaned filenames
            background.save(webp_output_path, "WEBP", quality=IMAGE_QUALITY)
            background.save(jpg_output_path, "JPEG", quality=IMAGE_QUALITY)
            print(f"Image processed and saved with cleaned filename: {webp_output_path}, {jpg_output_path}")

    except Exception as e:
        print(f"Error processing {input_path}: {e}")

def process_images_in_directory(input_directory):
    """
    Processes all images in the input directory and its subdirectories.
    Saves the processed images in 'styled_images/webp' and 'styled_images/jpg' folders.
    """
    for root, _, files in os.walk(input_directory):
        # Filter for images with valid formats
        image_files = [file for file in files if file.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
        if not image_files:
            continue  # Skip directories with no images

        # Create styled_images/webp and styled_images/jpg subdirectories
        webp_dir = os.path.join(root, "styled_images", "webp")
        jpg_dir = os.path.join(root, "styled_images", "jpg")
        create_directory(webp_dir)
        create_directory(jpg_dir)

        for file in image_files:
            input_path = os.path.join(root, file)
            webp_output_path = os.path.join(webp_dir, os.path.splitext(file)[0] + ".webp")
            jpg_output_path = os.path.join(jpg_dir, os.path.splitext(file)[0] + ".jpg")
            resize_and_center_image(input_path, webp_output_path, jpg_output_path)

if __name__ == "__main__":
    input_directory = "output/images"  # Input directory containing images
    print("Starting image resolution adjustment and conversion...")
    process_images_in_directory(input_directory)
    print("Image processing completed successfully.")