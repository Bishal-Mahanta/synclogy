import os
from ftplib import FTP
import pandas as pd
import logging

# FTP Configuration
FTP_HOST = "145.223.17.130"  # Replace with your FTP hostname
FTP_USER = "u501542776.bishal"  # Replace with your FTP username
FTP_PASS = "mLIwt4|QFO+8KE#8"  # Replace with your FTP password
FTP_BASE_URL = "https://data.synclogy.in/"  # Base URL for constructing image URLs

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def connect_to_ftp():
    """
    Connects to the FTP server and returns the connection object.
    """
    try:
        ftp = FTP(FTP_HOST)
        ftp.login(user=FTP_USER, passwd=FTP_PASS)
        logging.info("Connected to FTP server.")
        return ftp
    except Exception as e:
        logging.error(f"Failed to connect to FTP server: {e}")
        raise

def sanitize_path(path):
    """
    Cleans up a file or directory path for compatibility with FTP and URLs.
    """
    return path.replace(" ", "_").replace("(", "").replace(")", "").replace(",", "").strip()

def directory_exists(ftp, path):
    """
    Checks if a directory exists on the FTP server.
    """
    try:
        ftp.cwd(path)
        ftp.cwd("/")  # Return to root
        return True
    except Exception:
        return False

def create_remote_directory(ftp, remote_path):
    """
    Creates a directory on the FTP server, including all intermediate directories.
    """
    sanitized_path = sanitize_path(remote_path)
    directories = sanitized_path.split("/")
    current_path = ""
    for directory in directories:
        if directory:
            current_path = f"{current_path}/{directory}"
            if not directory_exists(ftp, current_path):
                try:
                    ftp.mkd(current_path)
                    logging.info(f"Created remote directory: {current_path}")
                except Exception as e:
                    logging.error(f"Failed to create directory {current_path}: {e}")

def upload_file(ftp, local_path, remote_path):
    """
    Uploads a single file to the FTP server and returns its public URL.
    """
    try:
        remote_path = sanitize_path(remote_path).lstrip("/")  # Ensure a sanitized path
        create_remote_directory(ftp, os.path.dirname(remote_path))
        with open(local_path, "rb") as file:
            ftp.storbinary(f"STOR {remote_path}", file)
            logging.info(f"Uploaded file: {remote_path}")
        # Construct the public URL
        cleaned_path = remote_path.replace("domains/synclogy.in/public_html/", "")
        return f"{FTP_BASE_URL}{cleaned_path}"
    except Exception as e:
        logging.error(f"Error uploading file {local_path} to {remote_path}: {e}")
        return None

def upload_styled_images(ftp, local_base_dir, remote_base_dir):
    """
    Uploads only WEBP files from 'styled_images' directories inside the local base directory.
    """
    uploaded_urls = []
    for root, dirs, files in os.walk(local_base_dir):
        # Look for styled_images directories
        if "styled_images" in root:
            relative_path = os.path.relpath(root, local_base_dir)
            remote_path = os.path.join(remote_base_dir, relative_path).replace("\\", "/")
            
            for file in files:
                if file.lower().endswith(".webp"):  # Upload only WEBP files
                    local_path = os.path.join(root, file)
                    remote_file_path = os.path.join(remote_path, file).replace("\\", "/")
                    file_url = upload_file(ftp, local_path, remote_file_path)
                    if file_url:
                        uploaded_urls.append({"File Name": file, "URL": file_url})
    return uploaded_urls

def save_urls_to_excel(uploaded_urls, output_file):
    """
    Saves a list of file URLs to an Excel sheet.
    """
    try:
        df = pd.DataFrame(uploaded_urls)
        df.to_excel(output_file, index=False)
        logging.info(f"Uploaded image URLs saved to {output_file}")
    except Exception as e:
        logging.error(f"Error saving URLs to Excel: {e}")
        raise

def main():
    """
    Main function to upload images and save their URLs.
    """
    local_directory = "output/images"  # Base directory to scan for styled_images
    remote_directory = "images"  # Remote base directory on the FTP server
    output_excel_file = "data/uploaded_image_links.xlsx"

    ftp = None
    try:
        ftp = connect_to_ftp()
        uploaded_urls = upload_styled_images(ftp, local_directory, remote_directory)
        save_urls_to_excel(uploaded_urls, output_excel_file)
        logging.info("Image upload and URL saving process completed successfully.")
    except Exception as e:
        logging.error(f"An error occurred: {e}")
    finally:
        if ftp:
            ftp.quit()
            logging.info("FTP connection closed.")

if __name__ == "__main__":
    main()
