# ------------------------------------- # 
# Project:          CCAS
# Objective:        Reading PDF

# Creator:          Tamara Munoz Ojeda
# Last Editor:      Tamara Munoz Ojeda

# Created:          06/11/2024
# Last Modified:    17/08/2025
# ------------------------------------- # 

# ------------------------------------- # 
# Importing necessary packages
import pandas as pd
import fitz
import re
import os
from openai import OpenAI
from dotenv import load_dotenv

# Importing repositories of own functions
from pdf_utilities import (
    construct_pdf_paths,
    extract_text_from_pdf,
    clean_pdf_text)

from openai_functions import (
    apply_gpt4,
    apply_gpt4mini)

# ------------------------------------- #
# Obtaining current working directory
current_path = os.getcwd()

# Defining path based on detected users
if '/Volumes/Crucial X9/' in current_path: # for server
    dropbox = '/Volumes/Crucial X9/tamaramunoz/ConsiliumBots Dropbox/Tamara Muñoz/CCAS 2022/CCAS 2024/Data/'
    desktop = '/Users/tamaramunoz/Documents/ConsiliumBots/CCAS/'
    pdf_path = os.path.join(dropbox, 'Inputs/Paper pdfs/')
else: # for local user
    dropbox = '/Users/tamaramunoz/ConsiliumBots Dropbox/Tamara Muñoz/CCAS 2022/CCAS 2024/Data/'
    desktop = '/Users/tamaramunoz/Desktop/ConsiliumBots/CCAS/'
    pdf_path = os.path.join(dropbox, 'Inputs/Paper pdfs/')

print(pdf_path)

# ------------------------------------- #
# Importing OpenAI API key
key_path = os.path.join(current_path, '.env')
load_dotenv(key_path)
OPENAI_API_KEY = os.getenv("API_KEY")
client = OpenAI(api_key = OPENAI_API_KEY)

# ------------------------------------- #
# Importing and creating df
df_path = os.path.join(dropbox, 'Inputs/ccas_papers.xlsx')
df = construct_pdf_paths(df_path, pdf_path)

# Adding new columns to dataframe for outputs of processing pdfs
df = df.assign(
    title = None, year = None, authors = None, summary = None, location = None,
    level_edu = None, relevance = None, reason_relevance = None, institutions = None, mechanisms = None,
    mechanisms_about = None, list_preferences = None, priority = None
)

# ------------------------------------- #
# Defining prompts for the gpt models
prompt_gpt_mini = """
I am analyzing papers related to Centralized Coordinated Assignment Systems (CCAS) in education markets. Therefore, I want to extract general information of the paper and its relevance to this topic. Please extract the following information and provide it in the specified format where each answer must be in '{}':

1. Title: [Title of the paper]
2. Year: [Year of publication]
3. Authors: [List of authors in "Last Name, First Name" format]
4. Summary: [Max 400 words]
5. Location of CCAS: [City/Cities, Country/Countries or 'Generic']
6. Level of Education of CCAS : [Pre-primary, Primary, Secondary, Tertiary, or 'no information']
"""

prompt_gpt4o = """
I am analyzing papers related to Centralized Coordinated Assignment Systems (CCAS) in education markets. Therefore, I want to extract information of the paper particularly on its relevance to this topic. Please extract the following information and provide it in the specified format where each answer must be in '{}':

1. Relevance (only the number): [3 (Highly Related: main focus is to analyze the coordinated system or its components), 2 (Moderately Related: describes coordinated assignment system or its components but it's not the main focus), 1 (Barely Related: mentions coordinated assignment system or its components but focuses on another topic), 9 (Not Related: completely unrelated to assignment systems or its components)]
2. Reason Relevance: [Justification for the relevance category, max 200 words]
3. Institutions: [Categories of the institutions that participate in the CCAS (e.g. public, private schools) or 'no information', these are not the insitutions mentioned in the authors acknowledgements]
4. Mechanisms (only abbreviation): [Deferred Acceptance (DA), Immediate Acceptance/Boston Mechanism (IA), Top Trading Cycle (TTC), Serial Dictatorship (SD), Others, Not-defined (ND)]
5. Mechanisms About: [Details about assignment mechanisms, max 100 words or 'no information']
6. List Preferences: [Length of the list of preferences for applicants or 'no information']
7. Priority Criteria: [Criteria for which applicants are given priority when applying and a brief explaining what it implies.]
"""

# Loop to process each paper
for index, row in df.iterrows():
    try:
        # Extract and clean PDF text
        pdf_text = extract_text_from_pdf(row['pdf'])
        if not pdf_text:
            print(f"No text extracted for index {index}. Skipping.")
            continue
        
        cleaned_text = clean_pdf_text(pdf_text)
        
        # First, process using GPT-4o-mini
        response_mini = apply_gpt4mini(client, cleaned_text, prompt_gpt_mini)
        print(f"Response from GPT-4o-mini for index {index}:\n{response_mini}\n")  # Debug: Print the response

        # Parse response for GPT-4o-mini
        lines_mini = response_mini.split('\n')
        if len(lines_mini) < 6:  # Expecting at least 6 lines from GPT-4o-mini response
            print(f"Unexpected response format from GPT-4o-mini for index {index}. Skipping.")
            continue

        # Define a dictionary to map column names to parsed values from GPT-4o-mini
        parsed_data_mini = {}
        expected_keys_mini = ['title', 'year', 'authors', 'summary', 'location', 'level_edu']

        for i, key in enumerate(expected_keys_mini):
            match = re.search(r'\{(.*)\}', lines_mini[i])  # Extract content within {}
            parsed_data_mini[key] = match.group(1).strip() if match else None  # Use matched content or None
        
        # Update the DataFrame with parsed values from GPT-4o-mini
        for key, value in parsed_data_mini.items():
            df.loc[index, key] = value

        # Then, process using GPT-4o
        response = apply_gpt4(client, cleaned_text, prompt_gpt4o)
        print(f"Response from GPT-4o for index {index}:\n{response}\n")  # Debug: Print the response

        # Filter empty lines from response
        lines = [line.strip() for line in response.split('\n') if line.strip()]
        print(f"Filtered response lines: {lines}")  # Debugging

        # Parse response for GPT-4o
        if len(lines) < 7:  # Expecting at least 7 lines from GPT-4o response
            print(f"Unexpected response format from GPT-4o for index {index}. Skipping.")
            continue

        # Define a dictionary to map column names to parsed values from GPT-4o
        parsed_data = {}
        expected_keys = [
            'relevance', 'reason_relevance', 'institutions',
            'mechanisms', 'mechanisms_about', 'list_preferences', 'priority'
        ]

        for i, key in enumerate(expected_keys):
            match = re.search(r'\{(.*)\}', lines[i])  # Extract content within {}
            parsed_data[key] = match.group(1).strip() if match else None  # Use matched content or None
        
        # Update the DataFrame with parsed values from GPT-4o
        for key, value in parsed_data.items():
            df.loc[index, key] = value

    except Exception as e:
        print(f"Error processing index {index}: {e}")


# Saving the DataFrame
output_path = os.path.join(dropbox, 'Intermediate/batch10.xlsx')
df.to_excel(output_path, index = False, engine = 'openpyxl')
print(f"Data saved to {output_path}")
