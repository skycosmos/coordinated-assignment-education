#!/usr/bin/env python3
"""
Test script to extract paper metadata and CCAS information using combined prompt.
Downloads 5 sample papers, extracts text, and tests combined analysis.
"""

import os
import json
import pandas as pd
import dropbox
from openai import OpenAI
import fitz

from ccas.paths import load_env, papers_output_dir
from ccas.papers.pdf_func import pdf2text
from ccas.papers.openai_func import read_paper

load_env()
_PAPERS_OUT = papers_output_dir()

def download_and_extract_papers(num_papers=None):
    """
    Download papers from Dropbox and extract text from first num_papers.
    
    Args:
        num_papers (int | None): Number of papers to process. None means all.
    
    Returns:
        list: List of dicts with paper info and extracted text
    """
    # Initialize Dropbox client
    dbx = dropbox.Dropbox(os.getenv("DROPBOX_ACCESS_TOKEN"))
    
    # Read paper list
    paper_list_path = _PAPERS_OUT / "paper_list.csv"
    df_papers = pd.read_csv(paper_list_path)
    
    # Keep only PDFs and optionally limit to first num_papers
    df_papers = df_papers[df_papers["type"] == ".pdf"].copy()
    papers_to_test = df_papers if num_papers is None else df_papers.head(num_papers)
    total_papers = len(papers_to_test)
    
    results = []
    
    for idx, row in papers_to_test.iterrows():
        paper_name = row['name']
        paper_path = row['path']
        
        print(f"[{idx+1}/{total_papers}] Processing: {paper_name}")
        
        try:
            # Download PDF from Dropbox to memory
            metadata, response = dbx.files_download(paper_path)
            pdf_bytes = response.content
            
            # Open PDF from bytes
            pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            # Extract and clean text
            cleaned_text = pdf2text(pdf_document)
            if not cleaned_text:
                raise ValueError("No extractable text found in PDF")
            
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


def test_combined_analysis(papers):
    """
    Test combined paper analysis using single prompt.
    
    Args:
        papers (list): List of paper dicts with extracted text
    
    Returns:
        list: List of analysis results
    """
    # Initialize OpenAI client
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    analysis_results = []
    
    for idx, paper in enumerate(papers):
        if paper['status'] != 'success':
            print(f"[{idx+1}] Skipping {paper['paper_name']} (status: {paper['status']})")
            analysis_results.append({
                'paper_name': paper['paper_name'],
                'analysis_result': None,
                'error': paper['status']
            })
            continue
        
        print(f"[{idx+1}] Analyzing {paper['paper_name']} with combined prompt")
        
        try:
            # Run combined analysis
            result = read_paper(
                client=client,
                paper_text=paper['text_sample'],
                model="gpt-4o",
                temp=0.2
            )
            
            # Strip markdown code blocks if present
            result_clean = result.strip()
            if result_clean.startswith('```json'):
                result_clean = result_clean[7:]  # Remove ```json
            if result_clean.startswith('```'):
                result_clean = result_clean[3:]  # Remove ```
            if result_clean.endswith('```'):
                result_clean = result_clean[:-3]  # Remove trailing ```
            result_clean = result_clean.strip()
            
            # Parse JSON result
            try:
                analysis_data = json.loads(result_clean)
                analysis_results.append({
                    'paper_name': paper['paper_name'],
                    'analysis_result': analysis_data,
                    'error': None
                })
                print(f"  ✓ Successfully analyzed: {paper['paper_name']}")
            except json.JSONDecodeError as e:
                analysis_results.append({
                    'paper_name': paper['paper_name'],
                    'analysis_result': result_clean,
                    'error': f'JSON parsing error: {str(e)[:100]}'
                })
                print(f"  ⚠ Response was not valid JSON: {str(e)[:100]}")
                
        except Exception as e:
            print(f"  ✗ Error during analysis: {e}")
            analysis_results.append({
                'paper_name': paper['paper_name'],
                'analysis_result': None,
                'error': str(e)
            })
    
    return analysis_results


def save_results(analysis_results):
    """
    Save combined analysis results to files.
    
    Args:
        analysis_results (list): List of analysis results
    """
    # Save full results as JSON
    json_path = _PAPERS_OUT / "combined_analysis_results.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(analysis_results, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Full results saved to {json_path}")
    
    # Create summary CSV with metadata
    metadata_summary = []
    for result in analysis_results:
        if result['analysis_result'] and not result['error']:
            metadata = result['analysis_result'].get('paper_metadata', {})
            metadata_summary.append({
                'paper_name': result['paper_name'],
                'title': metadata.get('title', 'Unknown'),
                'year': metadata.get('year', 'Unknown'),
                'authors': metadata.get('authors', 'Unknown'),
                'relevance': metadata.get('relevance', 'Unknown'),
                'summary': metadata.get('summary', ''),
            })
        else:
            metadata_summary.append({
                'paper_name': result['paper_name'],
                'title': 'Error',
                'year': 'N/A',
                'authors': 'N/A',
                'relevance': 'N/A',
                'summary': '',
            })
    
    df_metadata = pd.DataFrame(metadata_summary)
    metadata_path = _PAPERS_OUT / "paper_to_metadata.csv"
    df_metadata.to_csv(metadata_path, index=False)
    print(f"✓ Metadata summary saved to {metadata_path}")
    print("\nMetadata Summary:")
    print(df_metadata.to_string(index=False))
    
    # Create summary CSV with CCAS systems
    ccas_summary = []
    for result in analysis_results:
        if result['analysis_result'] and not result['error']:
            ccas_systems = result['analysis_result'].get('ccas_systems', [])
            if ccas_systems:
                for system in ccas_systems:
                    ccas_summary.append({
                        'paper_name': result['paper_name'],
                        'region': system.get('region', 'Unknown'),
                        'iso3_country_code': system.get('iso3_country_code', 'Unknown'),
                        'education_level': system.get('education_level', 'Unknown'),
                        'ccas_status': system.get('ccas_status', 'Unknown'),
                        'assignment_mechanism': system.get('assignment_mechanism', 'Unknown'),
                        'adoption_year': system.get('adoption_year', 'Unknown'),
                        'notes': system.get('notes', ''),
                    })
            else:
                ccas_summary.append({
                    'paper_name': result['paper_name'],
                    'region': 'No systems found',
                    'iso3_country_code': 'N/A',
                    'education_level': 'N/A',
                    'ccas_status': 'N/A',
                    'assignment_mechanism': 'N/A',
                    'adoption_year': 'N/A',
                    'notes': '',
                })
        else:
            ccas_summary.append({
                'paper_name': result['paper_name'],
                'region': 'Error',
                'iso3_country_code': 'N/A',
                'education_level': 'N/A',
                'ccas_status': 'N/A',
                'assignment_mechanism': 'N/A',
                'adoption_year': 'N/A',
                'notes': '',
            })
    
    df_ccas = pd.DataFrame(ccas_summary)
    ccas_path = _PAPERS_OUT / "paper_to_ccas_systems.csv"
    df_ccas.to_csv(ccas_path, index=False)
    print(f"\n✓ CCAS summary saved to {ccas_path}")
    print("\nCCAS Systems Summary:")
    print(df_ccas.to_string(index=False))


if __name__ == "__main__":
    print("=" * 80)
    print("Combined Paper Analysis - Full Dropbox Paper Set")
    print("=" * 80)
    
    # Step 1: Download and extract papers
    print("\nStep 1: Downloading and extracting text from all papers in list...")
    papers = download_and_extract_papers(num_papers=None)
    
    # Step 2: Run combined analysis
    print("\nStep 2: Running combined analysis (metadata + CCAS)...")
    results = test_combined_analysis(papers)
    
    # Step 3: Save results
    print("\nStep 3: Saving results...")
    save_results(results)
    
    print("\n" + "=" * 80)
    print("Combined analysis test completed!")
    print("=" * 80)
