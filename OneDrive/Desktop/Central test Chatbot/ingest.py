import os
import sys
from pinecone import Pinecone
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv(override=True)

# Prevent Windows console encoding crashes when printing non-ASCII.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# 1. Тохиргоо
gemini_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("testai")

def run_ingestion():
    file_path = "data.txt" # Файлын нэр яг ийм байх ёстой
    
    if not os.path.exists(file_path):
        print(f"ERROR: '{file_path}' файл олдсонгүй!")
        return

    print(f"Reading '{file_path}' ...")
    
    try:
        # utf-8-аас гадна өөр формат байх магадлалыг тооцож 'latin-1' эсвэл 'errors=ignore' ашиглав
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text_content = f.read()
            
        if not text_content:
            print("ERROR: Файл хоосон байна!")
            return

        print(f"Read {len(text_content)} characters. Vectorizing...")
        
        # Текстийг 2000 тэмдэгтээр хэсэгчлэх (Хэт их текст учир хэсгийг томрууллаа)
        chunk_size = 2000
        chunks = [text_content[i:i+chunk_size] for i in range(0, len(text_content), chunk_size)]
        
        for i, chunk in enumerate(chunks):
            # Вектор үүсгэх
            res = gemini_client.models.embed_content(
                model="models/gemini-embedding-001",
                contents=chunk,
                config=types.EmbedContentConfig(task_type="retrieval_document"),
            )
            vector = res.embeddings[0].values
            
            # Pinecone руу илгээх
            index.upsert(vectors=[{
                "id": f"chunk_{i}", 
                "values": vector, 
                "metadata": {"text": chunk}
            }])
            if i % 5 == 0: # 5 хэсэг тутамд мэдээлнэ
                print(f"Progress: {i+1}/{len(chunks)} chunks saved...")

        print("\nSUCCESS: Бүх дата Pinecone руу орж дууслаа.")

    except Exception as e:
        print(f"ERROR: Файл уншихад алдаа гарлаа: {e}")

if __name__ == "__main__":
    run_ingestion()