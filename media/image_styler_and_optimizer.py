import os
from PIL import Image

# Configuration
TARGET_RESOLUTION = (1664, 1664)  # Target image size (1664x1664)
BACKGROUND_COLOR = (255, 255, 255)  # White background color
IMAGE_QUALITY = 85  # Compression quality for WEBP format

def create_directory(path):
    """Creates a directory if it doesn't exist."""
    os.makedirs(path, exist_ok=True)

def resize_and_center_image(input_path, output_path):
    """
    Ensures the image resolution is 1664x1664.
    If not, resizes the image proportionally and centers it on a white background.
    """
    try:
        # Open the image
        with Image.open(input_path).convert("RGB") as img:  # Ensure RGB mode for WEBP

            # Check if the image already matches the target resolution
            if img.size == TARGET_RESOLUTION:
                img.save(output_path, "WEBP", quality=IMAGE_QUALITY)
                print(f"Image already 1664x1664, saved: {output_path}")
                return

            # Create a white background with the target resolution
            background = Image.new("RGB", TARGET_RESOLUTION, BACKGROUND_COLOR)

            # Resize the image proportionally using LANCZOS resampling
            img.thumbnail((TARGET_RESOLUTION[0], TARGET_RESOLUTION[1]), Image.Resampling.LANCZOS)

            # Calculate position to center the image
            x_offset = (TARGET_RESOLUTION[0] - img.size[0]) // 2
            y_offset = (TARGET_RESOLUTION[1] - img.size[1]) // 2

            # Paste the resized image onto the white background
            background.paste(img, (x_offset, y_offset))

            # Save the final image
            background.save(output_path, "WEBP", quality=IMAGE_QUALITY)
            print(f"Image resized, centered, and saved: {output_path}")

    except Exception as e:
        print(f"Error processing {input_path}: {e}")


def process_images_in_directory(input_directory):
    """
    Processes all images in the input directory and its subdirectories.
    Saves the processed images in 'styled_images' folders.
    """
    for root, _, files in os.walk(input_directory):
        # Filter for images with valid formats
        image_files = [file for file in files if file.lower().endswith(('.jpg', '.jpeg', '.png'))]
        if not image_files:
            continue  # Skip directories with no images

        # Create styled_images subdirectory in the current folder
        styled_images_dir = os.path.join(root, "styled_images")
        create_directory(styled_images_dir)

        for file in image_files:
            input_path = os.path.join(root, file)
            output_path = os.path.join(styled_images_dir, os.path.splitext(file)[0] + ".webp")
            resize_and_center_image(input_path, output_path)

if __name__ == "__main__":
    input_directory = "output/images"  # Input directory containing images
    print("Starting image resolution adjustment and conversion...")
    process_images_in_directory(input_directory)
    print("Image processing completed successfully.")
