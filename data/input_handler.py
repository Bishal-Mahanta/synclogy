import pandas as pd

def load_and_validate(filepath):
    """Loads the Excel file and validates its content."""
    try:
        df = pd.read_excel(filepath, sheet_name='Product List')
        required_columns = ['Product Name', 'Model Name', 'Color', 'Category']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"Missing required column: '{col}'")

        df['Product Name'] = df['Product Name'].str.strip().str.title()
        df['Model Name'] = df['Model Name'].str.strip().str.title()
        df['Color'] = df['Color'].str.strip().str.title()
        df['Category'] = df['Category'].str.strip().str.lower()

        if df[required_columns].isnull().any().any():
            raise ValueError("One or more required fields are missing values.")

        return df

    except FileNotFoundError:
        print(f"Error: File '{filepath}' not found.")
    except ValueError as e:
        print(f"Validation error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while loading the file: {e}")

    return None
