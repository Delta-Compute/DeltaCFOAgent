"""
Excel to CSV Converter
Converts Excel files (.xls, .xlsx) to CSV format for processing
"""
import pandas as pd
import os
from typing import Optional


def convert_excel_to_csv(excel_path: str, output_path: Optional[str] = None) -> str:
    """
    Convert Excel file to CSV format

    Args:
        excel_path: Path to Excel file (.xls or .xlsx)
        output_path: Optional path for output CSV. If not provided, uses same name with .csv extension

    Returns:
        Path to the converted CSV file

    Raises:
        ValueError: If file is not a valid Excel file
        Exception: If conversion fails
    """
    # Validate file extension
    file_ext = os.path.splitext(excel_path)[1].lower()
    if file_ext not in ['.xls', '.xlsx']:
        raise ValueError(f"File must be .xls or .xlsx, got: {file_ext}")

    # Determine output path
    if output_path is None:
        output_path = os.path.splitext(excel_path)[0] + '.csv'

    try:
        # Read Excel file
        # Try to read all sheets and use the first one with data
        excel_file = pd.ExcelFile(excel_path)

        # Get first sheet with data
        df = None
        for sheet_name in excel_file.sheet_names:
            temp_df = pd.read_excel(excel_file, sheet_name=sheet_name)
            if not temp_df.empty:
                df = temp_df
                print(f"Using sheet: {sheet_name}")
                break

        if df is None or df.empty:
            raise ValueError("No data found in Excel file")

        # Convert to CSV
        df.to_csv(output_path, index=False, encoding='utf-8')

        print(f"Successfully converted {excel_path} to {output_path}")
        print(f"Rows: {len(df)}, Columns: {len(df.columns)}")

        return output_path

    except Exception as e:
        raise Exception(f"Failed to convert Excel to CSV: {str(e)}")


def is_excel_file(filename: str) -> bool:
    """
    Check if filename has Excel extension

    Args:
        filename: Name of file to check

    Returns:
        True if file is Excel format
    """
    file_ext = os.path.splitext(filename)[1].lower()
    return file_ext in ['.xls', '.xlsx']
