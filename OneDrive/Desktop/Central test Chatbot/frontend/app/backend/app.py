import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from pinecone import Pinecone
from dotenv import load_dotenv

# Сүүлийн өөрчлөлтүүдийг ачаалах
load_dotenv(override=True)

# Windows дээрх Монгол үсгийн алдаанаас сэргийлэх
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

app = FastAPI()

# 1. CORS ТОХИРГОО (Frontend-ээс хандах зөвшөөрөл)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js ажиллаж байгаа хаяг
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. CLIENT-УУДЫГ ТОХИРУУЛАХ
gemini_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("testai")  # Таны Pinecone index-ийн нэр

class ChatRequest(BaseModel):
    message: str

# 3. RAG ЛОГИК: PINECONE-ООС ХАЙЛТ ХИЙХ ФУНКЦ
def get_context(query: str):
    try:
        # Асуултыг векторжуулах
        res = gemini_client.models.embed_content(
            model="models/gemini-embedding-001",
            contents=query
        )
        query_vector = res.embeddings[0].values

        # Pinecone-оос хамгийн ойр 3 хэсгийг хайх
        results = index.query(
            vector=query_vector,
            top_k=3,
            include_metadata=True
        )
        
        # Олдсон текстийг нэгтгэх
        context = "\n".join([match.metadata["text"] for match in results.matches])
        return context
    except Exception as e:
        print(f"Search Error: {e}")
        return ""

# 4. STREAM GENERATOR
async def generate_stream(user_prompt: str):
    # А. Контекст хайх (RAG)
    context = get_context(user_prompt)
    
    # Б. Системд өгөх заавар (System Prompt)
    full_prompt = f"""
    Чи бол Central Test-ийн ухаалаг туслах байна. 
    Доорх өгөгдсөн контекст мэдээллийг ашиглан хэрэглэгчийн асуултанд маш тодорхой, эелдэг хариулна уу.
    Хэрэв мэдээлэл байхгүй бол өөрийнхөө мэдлэгээр биш, харин 'Уучлаарай, энэ талаар мэдээлэл алга' гэж хариулаарай.

    Контекст:
    {context}

    Асуулт: {user_prompt}
    """

    try:
        response = gemini_client.models.generate_content_stream(
            model="gemini-2.0-flash",
            contents=full_prompt,
        )
        for chunk in response:
            if chunk.text:
                yield chunk.text
    except Exception as e:
        yield f"AI Error: {str(e)}"

@app.post("/chat")
async def chat(request: ChatRequest):
    if not request.message:
        raise HTTPException(status_code=400, detail="Message is empty")
    
    return StreamingResponse(
        generate_stream(request.message), 
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    import uvicorn
    # Streamlit ашиглахгүй тул StaticFiles-ийг түр хаслаа, Next.js тусдаа ажиллана
    uvicorn.run(app, host="127.0.0.1", port=8000)