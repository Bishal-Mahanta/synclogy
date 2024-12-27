import os
import logging
import shutil
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class BatchProcessor:
    def __init__(self, batch_root="batch"):
        self.batch_root = batch_root
        self._ensure_batch_root()

    def _ensure_batch_root(self):
        """Ensures the batch root directory exists"""
        os.makedirs(self.batch_root, exist_ok=True)

    def create_batch_directory(self) -> str:
        """
        Creates a new batch directory with timestamp and subdirectories
        
        Returns:
            str: Path to the created batch directory
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_dir = os.path.join(self.batch_root, timestamp)
        
        # Create main batch directory and subdirectories
        subdirs = ["data", "images", "logs"]
        for subdir in subdirs:
            os.makedirs(os.path.join(batch_dir, subdir), exist_ok=True)

        # Add file handler for this batch
        log_file = os.path.join(batch_dir, "logs", "batch.log")
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(file_handler)
        
        logging.info(f"Created batch directory: {batch_dir}")
        return batch_dir

    def process_files(self, files_config: dict, batch_dir: str) -> bool:
        """
        Process files according to their configuration
        
        Args:
            files_config: Dictionary with file paths and actions ('copy' or 'move')
            batch_dir: Path to the batch directory
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            for file_type, (filepath, action) in files_config.items():
                if not os.path.exists(filepath):
                    logging.warning(f"File not found: {filepath}")
                    continue

                dest_path = os.path.join(batch_dir, "data", os.path.basename(filepath))
                
                if action == 'copy':
                    shutil.copy2(filepath, dest_path)
                    logging.info(f"Copied {file_type} file to batch directory")
                else:  # move
                    shutil.move(filepath, dest_path)
                    logging.info(f"Moved {file_type} file to batch directory")
            
            return True
        except Exception as e:
            logging.error(f"Error processing files: {e}")
            return False

    def process_image_directory(self, image_dir: str, batch_dir: str) -> bool:
        """
        Process the image directory by moving all contents to the batch 'images' subdirectory.

        Args:
            image_dir: Path to the source image directory.
            batch_dir: Path to the batch directory.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            dest_image_dir = os.path.join(batch_dir, "images")
            
            if os.path.exists(image_dir):
                # Move all contents of image_dir to dest_image_dir
                os.makedirs(dest_image_dir, exist_ok=True)
                for filename in os.listdir(image_dir):
                    source_path = os.path.join(image_dir, filename)
                    dest_path = os.path.join(dest_image_dir, filename)
                    
                    if os.path.isfile(source_path):
                        shutil.move(source_path, dest_path)
                    elif os.path.isdir(source_path):
                        shutil.move(source_path, dest_path)
                
                logging.info(f"Moved all contents of '{image_dir}' to '{dest_image_dir}'")
                
                # Recreate the original image_dir for next batch
                os.makedirs(image_dir, exist_ok=True)
                logging.info(f"Recreated empty directory: '{image_dir}'")
                return True
            else:
                logging.warning(f"Image directory not found: {image_dir}")
                return False
        except Exception as e:
            logging.error(f"Error processing image directory: {e}")
            return False

    def process_batch(self, input_filepath: str, output_filepath: str, image_links_filepath: str, log_file: str, image_dir: str) -> bool:
        """
        Process a complete batch including all files and directories
        
        Args:
            input_filepath: Path to the input Excel file
            output_filepath: Path to the output Excel file
            image_links_filepath: Path to the image links Excel file
            log_file: Path to the log file
            image_dir: Path to the image directory
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create batch directory
            batch_dir = self.create_batch_directory()
            
            # Define files to process
            files_config = {
                'input': (input_filepath, 'move'),
                'output': (output_filepath, 'move'),
                'image_links': (image_links_filepath, 'move'),
                'logs': (log_file, 'move')  # Move log file to "logs" subdirectory
            }
            
            # Process files
            if not self.process_files(files_config, batch_dir):
                return False
            
            # Process image directory
            if not self.process_image_directory(image_dir, batch_dir):
                return False
            
            logging.info(f"Batch processing completed successfully: {batch_dir}")
            return True
            
        except Exception as e:
            logging.error(f"Error in batch processing: {e}")
            return False


if __name__ == "__main__":
    # Example usage
    processor = BatchProcessor()
    
    input_filepath = "data/product_data.xlsx"
    output_filepath = "data/output_scraper_results.xlsx"
    image_links_filepath = "data/uploaded_image_links.xlsx"
    
    processor.process_batch(input_filepath, output_filepath, image_links_filepath)