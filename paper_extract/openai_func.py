# -------------------------------------- #
# Project:          CCAS
# Objective:        OpenAI Functions

# Creator:          Tamara Munoz Ojeda
# Last Editor:      Tamara Munoz Ojeda

# Created:          21/11/2024
# Last Modified:    17/08/2025
# -------------------------------------- # 

# The object of this file is to define functions that call different OpenAI models. They are fairly standard code and specify the model, message, roles, output, and creativity of each model. They are the following:  
# 'apply_gpt4': calls the gpt-4o model 
# 'apply_gpt4mini': calls the gpt-4o mini model 
# 'apply_gpt5mini': calls the gpt-5 mini model 

# Importing necessary packages
from openai import OpenAI
from prompt_gen import generate_ccas_extraction_prompt


# -------------------------------------- #
def extract_ccas_from_paper(client, paper_text, model="gpt-4o", temp=0.2):
    """
    Extract CCAS (Coordinated Choice and Assignment System) information from academic paper text.
    
    Designed to handle papers discussing multiple regions and gracefully handle missing information.
    Combines prompt generation and OpenAI API call in a single function.
    
    Args:
        client (OpenAI): OpenAI API client initialized with the API key.
        paper_text (str): The academic paper text to analyze.
        model (str, optional): OpenAI model to use. Default is "gpt-4o".
                              Options: "gpt-4o", "gpt-4o-mini", "gpt-5-mini"
        temp (float, optional): Temperature for response generation. Default is 0.2 (low randomness for structured output).
    
    Returns:
        str: JSON object(s) containing extracted CCAS information. Returns array if multiple regions found,
             single object if one region found, or error object if no relevant information found.
    """
    try:
        # Generate CCAS extraction prompt from prompt_gen module
        prompt = generate_ccas_extraction_prompt()
        
        # Setting up the OpenAI message format
        messages = [
            {"role": "system", "content": prompt},  
            {"role": "user", "content": paper_text}
        ]
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temp
        )
        
        # Obtaining response from OpenAI
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error when extracting CCAS from paper with {model}: {e}")
        return '{"error": "Failed to extract CCAS information", "details": "' + str(e) + '"}')   