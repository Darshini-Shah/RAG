import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.environ.get('GEMINI_API_KEY'))

print("Testing direct genai.embed_content...")
models = ["models/text-embedding-004", "models/embedding-001"]

for m in models:
    try:
        res = genai.embed_content(model=m, content="test", task_type="retrieval_document")
        print(f"SUCCESS with {m} directly!")
    except Exception as e:
        print(f"FAILED with {m} directly: {e}")

print("\nTesting with version='v1'...")
for m in models:
    try:
        # Note: genai.embed_content doesn't take version, but we can check if there's a different way
        pass 
    except: pass
