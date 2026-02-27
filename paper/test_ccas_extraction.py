#!/usr/bin/env python3
"""
Test script to extract CCAS information from academic papers using OpenAI.
Downloads first 5 papers from Dropbox, extracts text, and tests CCAS extraction prompts.
"""

import os
import json
import pandas as pd
import dropbox
from dotenv import load_dotenv
from openai import OpenAI
from pdf_utilities import extract_text_from_pdf, clean_pdf_text
from openai_functions import extract_ccas_from_paper
import fitz  # PyMuPDF for PDF processing
import io

# Load environment variables
load_dotenv()

def download_and_extract_papers(num_papers=5):
    """
    Download papers from Dropbox and extract text from first num_papers.
    
    Args:
        num_papers (int): Number of papers to test
    
    Returns:
        list: List of dicts with paper info and extracted text
    """
    # Initialize Dropbox client
    dbx = dropbox.Dropbox(os.getenv("DROPBOX_ACCESS_TOKEN"))
    
    # Read paper list
    paper_list_path = "output/paper_list.csv"
    df_papers = pd.read_csv(paper_list_path)
    
    # Get first num_papers
    papers_to_test = df_papers.head(num_papers)
    
    results = []
    
    for idx, row in papers_to_test.iterrows():
        paper_name = row['name']
        paper_path = row['path']
        
        print(f"[{idx+1}/{num_papers}] Processing: {paper_name}")
        
        try:
            # Download PDF from Dropbox to memory
            metadata, response = dbx.files_download(paper_path)
            pdf_bytes = response.content
            
            # Open PDF from bytes
            pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            # Extract text
            text = extract_text_from_pdf(pdf_document)
            cleaned_text = clean_pdf_text(text)
            
            # Limit text to first 8000 chars for API efficiency
            text_sample = cleaned_text[:8000]
            
            results.append({
                'paper_name': paper_name,
                'paper_path': paper_path,
                'text_length': len(cleaned_text),
                'text_sample': text_sample,
                'status': 'success'
            })
            
            print(f"  ✓ Successfully extracted {len(cleaned_text)} characters")
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            results.append({
                'paper_name': paper_name,
                'paper_path': paper_path,
                'text_length': 0,
                'text_sample': '',
                'status': f'error: {str(e)}'
            })
    
    return results


def test_ccas_extraction(papers):
    """
    Test CCAS extraction on papers using OpenAI.
    
    Args:
        papers (list): List of paper dicts with extracted text
    
    Returns:
        list: List of extraction results with CCAS findings
    """
    # Initialize OpenAI client
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    extraction_results = []
    
    for idx, paper in enumerate(papers):
        if paper['status'] != 'success':
            print(f"[{idx+1}] Skipping {paper['paper_name']} (status: {paper['status']})")
            extraction_results.append({
                'paper_name': paper['paper_name'],
                'ccas_result': None,
                'error': paper['status']
            })
            continue
        
        print(f"[{idx+1}] Extracting CCAS info from {paper['paper_name']}")
        
        try:
            # Extract CCAS information
            result = extract_ccas_from_paper(
                client=client,
                paper_text=paper['text_sample'],
                model="gpt-4o-mini",  # Using mini for cost efficiency in testing
                temp=0.2
            )
            
            # Parse JSON result
            try:
                ccas_data = json.loads(result)
                extraction_results.append({
                    'paper_name': paper['paper_name'],
                    'ccas_result': ccas_data,
                    'error': None
                })
                print(f"  ✓ Successfully extracted CCAS data")
            except json.JSONDecodeError as e:
                extraction_results.append({
                    'paper_name': paper['paper_name'],
                    'ccas_result': result,
                    'error': f'JSON parsing error: {str(e)}'
                })
                print(f"  ⚠ Response was not valid JSON: {str(e)[:100]}")
                
        except Exception as e:
            print(f"  ✗ Error during extraction: {e}")
            extraction_results.append({
                'paper_name': paper['paper_name'],
                'ccas_result': None,
                'error': str(e)
            })
    
    return extraction_results


def save_results(extraction_results):
    """
    Save extraction results to CSV and JSON files.
    
    Args:
        extraction_results (list): List of extraction results
    """
    # Save full results as JSON
    json_path = "output/ccas_extraction_results.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(extraction_results, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Full results saved to {json_path}")
    
    # Create summary CSV
    summary_data = []
    for result in extraction_results:
        if result['ccas_result'] and not result['error']:
            # Handle both single dict and list of dicts
            ccas_items = result['ccas_result'] if isinstance(result['ccas_result'], list) else [result['ccas_result']]
            for item in ccas_items:
                if isinstance(item, dict):
                    summary_data.append({
                        'paper_name': result['paper_name'],
                        'region': item.get('region', 'Unknown'),
                        'iso3_country_code': item.get('iso3_country_code', 'Unknown'),
                        'education_level': item.get('education_level', 'Unknown'),
                        'ccas_status': item.get('ccas_status', 'Unknown'),
                        'assignment_mechanism': item.get('assignment_mechanism', 'Unknown'),
                        'adoption_year': item.get('adoption_year', 'Unknown'),
                    })
        else:
            summary_data.append({
                'paper_name': result['paper_name'],
                'region': 'Error',
                'iso3_country_code': 'N/A',
                'education_level': 'N/A',
                'ccas_status': 'N/A',
                'assignment_mechanism': 'N/A',
                'adoption_year': 'N/A',
            })
    
    df_summary = pd.DataFrame(summary_data)
    csv_path = "output/ccas_extraction_summary.csv"
    df_summary.to_csv(csv_path, index=False)
    print(f"✓ Summary results saved to {csv_path}")
    print("\nSummary:")
    print(df_summary.to_string(index=False))


if __name__ == "__main__":
    print("=" * 70)
    print("CCAS Extraction Test - Processing 5 Academic Papers")
    print("=" * 70)
    
    # Step 1: Download and extract papers
    print("\nStep 1: Downloading and extracting text from papers...")
    papers = download_and_extract_papers(num_papers=5)
    
    # Step 2: Test CCAS extraction
    print("\nStep 2: Testing CCAS extraction with OpenAI...")
    results = test_ccas_extraction(papers)
    
    # Step 3: Save results
    print("\nStep 3: Saving results...")
    save_results(results)
    
    print("\n" + "=" * 70)
    print("Test completed!")
    print("=" * 70)
