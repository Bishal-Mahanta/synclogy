import os
from PIL import Image

# Configuration
TARGET_RESOLUTION = (1664, 1664)  # Target image size (1664x1664)
BACKGROUND_COLOR = (255, 255, 255)  # White background color
IMAGE_QUALITY = 85  # Compression quality for WEBP format

def create_directory(path):
    """Creates a directory if it doesn't exist."""
    os.makedirs(path, exist_ok=True)

def resize_and_center_image(input_path, webp_output_path, png_output_path):
    """
    Resizes the image to 1000x1000 (if necessary) and centers it on a 1664x1664 white background.
    Saves the output as both WEBP and PNG files.
    """
    try:
        # Open the image
        with Image.open(input_path).convert("RGB") as img:
            # Check if the image is already 1664x1664
            if img.size == TARGET_RESOLUTION:
                # If the image is already 1664x1664, save it as WEBP and PNG without changes
                img.save(webp_output_path, "WEBP", quality=IMAGE_QUALITY)
                img.save(png_output_path, "PNG")
                print(f"Image already 1664x1664, saved as WEBP and PNG: {webp_output_path}, {png_output_path}")
                return

            # Resize to a maximum of 1000x1000
            max_inner_resolution = (1500, 1500)
            img.thumbnail(max_inner_resolution, Image.Resampling.LANCZOS)

            # Create a white background of 1664x1664
            background = Image.new("RGB", TARGET_RESOLUTION, BACKGROUND_COLOR)

            # Center the resized image onto the white background
            x_offset = (TARGET_RESOLUTION[0] - img.size[0]) // 2
            y_offset = (TARGET_RESOLUTION[1] - img.size[1]) // 2

            background.paste(img, (x_offset, y_offset))

            # Save the final image as WEBP and PNG
            background.save(webp_output_path, "WEBP", quality=IMAGE_QUALITY)
            background.save(png_output_path, "PNG")
            print(f"Image resized, centered, and saved as 1664x1664 WEBP and PNG: {webp_output_path}, {png_output_path}")

    except Exception as e:
        print(f"Error processing {input_path}: {e}")

def process_images_in_directory(input_directory):
    """
    Processes all images in the input directory and its subdirectories.
    Saves the processed images in 'styled_images/webp' and 'styled_images/png' folders.
    """
    for root, _, files in os.walk(input_directory):
        # Filter for images with valid formats
        image_files = [file for file in files if file.lower().endswith((".jpg", ".jpeg", ".png"))]
        if not image_files:
            continue  # Skip directories with no images

        # Create styled_images/webp and styled_images/png subdirectories
        webp_dir = os.path.join(root, "styled_images", "webp")
        png_dir = os.path.join(root, "styled_images", "png")
        create_directory(webp_dir)
        create_directory(png_dir)

        for file in image_files:
            input_path = os.path.join(root, file)
            webp_output_path = os.path.join(webp_dir, os.path.splitext(file)[0] + ".webp")
            png_output_path = os.path.join(png_dir, os.path.splitext(file)[0] + ".png")
            resize_and_center_image(input_path, webp_output_path, png_output_path)

if __name__ == "__main__":
    input_directory = "output/images"  # Input directory containing images
    print("Starting image resolution adjustment and conversion...")
    process_images_in_directory(input_directory)
    print("Image processing completed successfully.")