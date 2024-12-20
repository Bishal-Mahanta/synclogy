import os
import pandas as pd
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

INPUT_DIRECTORY = "data/input"
REQUIRED_COLUMNS = ["Product Name", "Category", "Model Name", "Color", "Link"]

def find_input_file(input_directory):
    """
    Finds the most recent Excel file in the specified directory.
    
    Parameters:
        input_directory (str): Directory to search for Excel files.
    
    Returns:
        str: Path to the most recent Excel file, or None if no file is found.
    """
    try:
        # List all files in the directory
        files = [
            os.path.join(input_directory, f)
            for f in os.listdir(input_directory)
            if f.endswith(('.xls', '.xlsx'))
        ]

        if not files:
            logging.error(f"No Excel files found in the directory: {input_directory}")
            return None

        # Find the most recently modified file
        recent_file = max(files, key=os.path.getmtime)
        logging.info(f"Found input file: {recent_file}")
        return recent_file
    except Exception as e:
        logging.error(f"Error finding input file: {e}")
        return None

def load_input_data(filepath):
    """
    Loads and validates input data from an Excel file.
    
    Parameters:
        filepath (str): Path to the input Excel file.
    
    Returns:
        DataFrame: Validated and preprocessed data as a pandas DataFrame.
    """
    try:
        logging.info(f"Loading input data from: {filepath}")
        data = pd.read_excel(filepath)

        # Check if the file is empty
        if data.empty:
            logging.error(f"Input file '{filepath}' is empty.")
            return None
        
        # Validate required columns
        missing_columns = [col for col in REQUIRED_COLUMNS if col not in data.columns]
        if missing_columns:
            logging.error(f"Missing required columns: {', '.join(missing_columns)}")
            return None

        # Preprocess data
        for col in data.select_dtypes(include=["object"]).columns:
            data[col] = data[col].str.strip()  # Remove leading/trailing whitespace
        
        # Optional: Generate a search query column
        data["Search Query"] = data.apply(
            lambda row: f"{row['Product Name']} {row['Model Name']} {row['Color']}".strip(),
            axis=1
        )

        logging.info("Input data loaded and validated successfully.")
        return data
    except FileNotFoundError:
        logging.error(f"File not found: {filepath}")
        return None
    except Exception as e:
        logging.error(f"Error loading input file: {e}")
        return None
