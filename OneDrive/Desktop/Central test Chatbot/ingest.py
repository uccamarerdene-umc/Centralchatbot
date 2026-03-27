import os
from pinecone import Pinecone
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv(override=True)

# 1. Тохиргоо
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("testai")

def run_ingestion():
    file_path = "data.txt" # Файлын нэр яг ийм байх ёстой
    
    if not os.path.exists(file_path):
        print(f"❌ Алдаа: '{file_path}' файл олдсонгүй!")
        return

    print(f"📖 '{file_path}' файлыг уншиж байна...")
    
    try:
        # utf-8-аас гадна өөр формат байх магадлалыг тооцож 'latin-1' эсвэл 'errors=ignore' ашиглав
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text_content = f.read()
            
        if not text_content:
            print("❌ Алдаа: Файл хоосон байна!")
            return

        print(f"🔄 Нийт {len(text_content)} тэмдэгт уншлаа. Вектор болгож байна...")
        
        # Текстийг 2000 тэмдэгтээр хэсэгчлэх (Хэт их текст учир хэсгийг томрууллаа)
        chunk_size = 2000
        chunks = [text_content[i:i+chunk_size] for i in range(0, len(text_content), chunk_size)]
        
        for i, chunk in enumerate(chunks):
            # Вектор үүсгэх
            res = genai.embed_content(
                model="models/gemini-embedding-001", 
                content=chunk,
                task_type="retrieval_document"
            )
            vector = res["embedding"]
            
            # Pinecone руу илгээх
            index.upsert(vectors=[{
                "id": f"chunk_{i}", 
                "values": vector, 
                "metadata": {"text": chunk}
            }])
            if i % 5 == 0: # 5 хэсэг тутамд мэдээлнэ
                print(f"✅ Процесс: {i+1}/{len(chunks)} хэсэг хадгалагдлаа...")

        print("\n🎉 АМЖИЛТТАЙ! Бүх дата Pinecone руу орж дууслаа.")

    except Exception as e:
        print(f"❌ Файл уншихад алдаа гарлаа: {e}")

if __name__ == "__main__":
    run_ingestion()