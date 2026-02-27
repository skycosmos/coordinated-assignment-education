# ----------------------------------------------- #
# Project:          CCAS
# Objective:        Functions for processing PDFs

# Creator:          Tamara Munoz Ojeda
# Last Editor:      Tamara Munoz Ojeda

# Created:          21/11/2024
# Last Modified:    21/11/2024
# ----------------------------------------------- # 

# The object of this file is to define the function that will be used in order to process papers of the project CCAS.
# 'extract_text_from_pdf': extracts the text from a pdf file and cleans it by normalizing the white spaces.

import pandas as pd
import fitz
import re

# ----------------------------------------------- # 
def extract_text_from_pdf(pdf_document, debug = False):
    """
    Extracts text from a PDF file and cleans it by normalizing whitespace.

    Args:
        pdf_document (fitz.Document): The PDF document object.
        debug (bool): Whether to enable debug logging for errors.

    Returns:
        str: Extracted text from the PDF, or None if an error occurs.
    """

    try:
        text = ""
        for page in pdf_document:
            text += page.get_text()
        return re.sub(r'\s+', ' ', text.strip())

    except Exception as e:
        if debug:
            print(f"Error extracting text from PDF document: {e}")
        return None