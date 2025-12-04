# ----------------------------------------------- #
# Project:          CCAS
# Objective:        Functions for processing PDFs

# Creator:          Tamara Munoz Ojeda
# Last Editor:      Tamara Munoz Ojeda

# Created:          21/11/2024
# Last Modified:    21/11/2024
# ----------------------------------------------- # 

# The object of this file is to define different functions that will be used in order to process papers of the proyect CCAS. It contains the following functions:
# 'construct_pdf_paths': based on a list of file names, it contructs the paths for all the pdfs within the file
# 'extract_text_from_pdf': extracts the text from a pdf file
# 'clean_pdf_text': cleans text extracted from pdf


# Importing necessary packages for each function
import os
import pandas as pd
import fitz
import re


# ----------------------------------------------- # 
def construct_pdf_paths(source_file, base_path, output_column = 'pdf'):
    """
    Constructs paths for pdfs dynamically based on a source_name column in an Excel file.
    
    Args:
        source_file (str): Path to the Excel file containing the source_name column.
        base_path (str): Base path where the PDF files are stored.
        output_column (str): Name of the new column to store constructed paths.
    
    Returns:
        pd.DataFrame: DataFrame with source_name and constructed PDF paths.
    """
    try:
        # Loading source_name column from Excel file
        df = pd.read_excel(source_file, usecols = ['source_name'])
        
        # Validating 'source_name' values
        if df['source_name'].isnull().any():
            print("Warning: Some 'source_name' values are missing. These rows will have invalid PDF paths.")
        
        # Constructing PDF paths
        df[output_column] = df['source_name'].apply(
            lambda name: os.path.join(base_path, f"{name}.pdf") if pd.notnull(name) else None
        )
        
        # Checking if files exist
        df['file_exists'] = df[output_column].apply(lambda path: os.path.exists(path) if path else False)
        
        # Loging missing files
        missing_files = df[df['file_exists'] == False]
        if not missing_files.empty:
            print(f"Warning: {len(missing_files)} files are missing. Example missing files:")
            print(missing_files.head())
        
        # Droping the file_exists column before returning if unnecessary
        df.drop(columns=['file_exists'], inplace = True)

        return df
    except Exception as e:
        print(f"Error constructing PDF paths: {e}")
        return None


# ----------------------------------------------- # 
def extract_text_from_pdf(pdf_path, debug = False):
    """
    Extracts text from a PDF file.

    Args:
        pdf_path (str): Path to the PDF file.
        debug (bool): Whether to enable debug logging for errors.

    Returns:
        str: Extracted text from the PDF, or None if an error occurs.
    """
    if not os.path.exists(pdf_path):
        if debug:
            print(f"Error: File not found, corresponding path: {pdf_path}")
        return None

    try:
        text = ""
        with fitz.open(pdf_path) as pdf:
            for page in pdf:
                text += page.get_text()
        return text
    except Exception as e:
        if debug:
            print(f"Error extracting text from {pdf_path}: {e}")
        return None
   

# ----------------------------------------------- # 
def clean_pdf_text(pdf_text):
    """
    Cleans the extracted text by normalizing whitespace.

    Args:
        pdf_text (str): The raw text extracted from a PDF.

    Returns:
        str: Cleaned text with normalized spaces.
    """
    if not pdf_text:
        return ""  # Return empty string for None or empty inputs

    return re.sub(r'\s+', ' ', pdf_text.strip())
