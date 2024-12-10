import pandas as pd
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_input_data(filepath):
    """
    Loads input data from an Excel file without validation.
    
    Parameters:
        filepath (str): Path to the input Excel file.
    
    Returns:
        DataFrame: Loaded data as a pandas DataFrame, or None if loading fails.
    """
    try:
        logging.info(f"Loading input data from: {filepath}")
        data = pd.read_excel(filepath)
        logging.info("Input data loaded successfully.")
        return data
    except FileNotFoundError:
        logging.error(f"File not found: {filepath}")
        return None
    except Exception as e:
        logging.error(f"Error loading input file: {e}")
        return None
