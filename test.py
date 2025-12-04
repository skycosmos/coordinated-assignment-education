from dotenv import load_dotenv
from openai import OpenAI
import dropbox
import os

load_dotenv()

# Test OpenAI API Key
def test_api_key():
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hello"}]
        )
        print("API key works! Response:", response.choices[0].message.content)
    except Exception as e:
        print("Error:", e)

# Test Dropbox Access Token
def test_dropbox_token(token: str = os.getenv("DROPBOX_ACCESS_TOKEN"), path: str = os.getenv("DROPBOX_PATH")):
    try:
        dbx = dropbox.Dropbox(token)
        # Test by listing the default folder
        result = dbx.files_list_folder(path)
        print("✔ Dropbox token works! Files/folders in Dropbox default folder:")
        for entry in result.entries:
            print("  -", entry.name)

    except dropbox.exceptions.AuthError as e:
        print("❌ Invalid Dropbox token:", e)
    except Exception as e:
        print("❌ Error occurred:", e)


if __name__ == "__main__":
    test_api_key()
    test_dropbox_token()
