# ============================================
# Dropbox File Listing Module
# ============================================
import pandas as pd
import os

import dropbox  # Dropbox API client
from dotenv import load_dotenv  # Environment variable management

# Load environment variables (including DROPBOX_ACCESS_TOKEN)
load_dotenv()

def list_dropbox_files(dbx: dropbox.Dropbox, folder_path: str):
    """
    Return a DataFrame listing all files (excluding folders) from a Dropbox folder.
    
    Parameters:
        dbx (dropbox.Dropbox): Authenticated Dropbox client
        folder_path (str): Dropbox folder path to list
    
    Returns:
        pd.DataFrame: DataFrame with columns [name, path, type]
                      - name: File name
                      - path: Full file path in Dropbox
                      - type: File extension (e.g., '.pdf', '.txt')
                      Folders are excluded from results.
    """

    all_entries = []

    try:
        # Get initial folder listing (recursive=True for subdirectories)
        result = dbx.files_list_folder(folder_path, recursive=True)

        # Paginate through results
        while True:
            # Process each entry in the current batch
            for entry in result.entries:
                # Only process files, skip folders
                if isinstance(entry, dropbox.files.FileMetadata):
                    file_type = os.path.splitext(entry.name)[1].lower()
                    all_entries.append({
                        "name": entry.name,
                        "path": entry.path_display,
                        "type": file_type if file_type else "unknown"
                    })

            # Check if there are more results to fetch
            if not result.has_more:
                break

            # Fetch next page of results
            result = dbx.files_list_folder_continue(result.cursor)

    except Exception as e:
        print("Error:", e)
        return None

    return pd.DataFrame(all_entries)


# ============================================
# Main Execution
# ============================================

# Initialize Dropbox client
dbx = dropbox.Dropbox(os.getenv("DROPBOX_ACCESS_TOKEN"))
folder_path = "/CCAS 2022/CCAS 2024/Data/Inputs/Paper pdfs"

# Retrieve list of files from Dropbox folder
df = list_dropbox_files(dbx, folder_path)
print(df.head())

# Create output directory if it doesn't exist
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)
df.to_csv(os.path.join(output_dir, "paper_list.csv"), index=False)
print(f"CSV saved to {output_dir}/paper_list.csv")