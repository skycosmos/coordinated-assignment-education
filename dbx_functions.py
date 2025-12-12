import pandas as pd
import os
import dropbox
from dotenv import load_dotenv

load_dotenv()

def list_dropbox_files(dbx: dropbox.Dropbox, folder_path: str):
    """
    Return a DataFrame listing all files and folders under a Dropbox folder.
    Columns: name, path, type
    """
    all_entries = []

    try:
        result = dbx.files_list_folder(folder_path, recursive=True)

        while True:
            for entry in result.entries:
                if isinstance(entry, dropbox.files.FileMetadata):
                    file_type = os.path.splitext(entry.name)[1].lower()
                    all_entries.append({
                        "name": entry.name,
                        "path": entry.path_display,
                        "type": file_type if file_type else "unknown"
                    })
                elif isinstance(entry, dropbox.files.FolderMetadata):
                    all_entries.append({
                        "name": entry.name,
                        "path": entry.path_display,
                        "type": "folder"
                    })

            if not result.has_more:
                break

            result = dbx.files_list_folder_continue(result.cursor)

    except Exception as e:
        print("Error:", e)
        return None

    return pd.DataFrame(all_entries)


dbx = dropbox.Dropbox(os.getenv("DROPBOX_ACCESS_TOKEN"))
folder_path = "/CCAS 2022/CCAS 2024/Data/Inputs/Paper pdfs"

df = list_dropbox_files(dbx, folder_path)
print(df.head())