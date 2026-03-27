import os
import json
import asyncio
import sys
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types
from pinecone import Pinecone
from dotenv import load_dotenv

# .env файлаас нууц түлхүүрүүдийг унших (override=True нь систем дэх хуучин түлхүүрийг дарах зориулалттай)
load_dotenv(override=True)

# Prevent Windows console encoding crashes when logging Mongolian text.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

app = FastAPI()

# Frontend-ээс хандах эрх нээх
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gemini болон Pinecone тохиргоо
api_key = os.getenv("GOOGLE_API_KEY")
genai_client = genai.Client(api_key=api_key)

pinecone_api_key = os.getenv("PINECONE_API_KEY")
pc = Pinecone(api_key=pinecone_api_key)

# Pinecone Index нэр (Таны Index нэр 'testai' мөн эсэхийг шалгаарай)
index_name = "testai"
index = pc.Index(index_name)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("--- Шинэ хэрэглэгч холбогдлоо ---")
    
    try:
        while True:
            # 1. Хэрэглэгчээс дата хүлээж авах
            raw_data = await websocket.receive_text()
            print(f"Ирсэн дата: {raw_data}")
            
            try:
                data_json = json.loads(raw_data)
                query = data_json.get("message", raw_data) # Хэрэв JSON биш бол шууд текст гэж үзнэ
            except json.JSONDecodeError:
                query = raw_data

            # 2. Pinecone-оос хайх (Embedding үүсгэх)
            print(f"Хайж байна: {query}")
            try:
                embed_res = genai_client.models.embed_content(
                    model="gemini-embedding-001",
                    contents=query,
                    config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY")
                )
                query_vector = embed_res.embeddings[0].values
                
                search_results = index.query(vector=query_vector, top_k=3, include_metadata=True)
                
                # Metadata дотор 'text' гэсэн талбар байгаа гэж үзэв
                contexts = []
                for match in search_results["matches"]:
                    if "text" in match["metadata"]:
                        contexts.append(match["metadata"]["text"])
                
                context_text = "\n".join(contexts)
            except Exception as e:
                print(f"Pinecone хайлтад алдаа гарлаа: {e}")
                context_text = "Мэдээллийн сангаас мэдээлэл олдсонгүй."

            # 3. Gemini-ээр хариулт үүсгэх (Streaming)
            # ТАЙЛБАР: 'gemini-1.5-flash' нь одоогоор хамгийн сайн ажиллаж байгаа нэршил юм.
            model = genai.GenerativeModel("gemini-2.5-flash")
            
            # ТАЙЛБАР: 'gemini-1.5-flash' нь одоогоор хамгийн сайн ажиллаж байгаа нэршил юм.
            model = genai.GenerativeModel("gemini-2.5-flash")
            
            # ТАЙЛБАР: 'gemini-1.5-flash' нь одоогоор хамгийн сайн ажиллаж байгаа нэршил юм.
            model = genai.GenerativeModel("gemini-2.5-flash")
            
            prompt = (
                f"Чи бол Central Test компанийн албан ёсны зөвлөх AI байна. "
                Чи бол Central Test компанийн AI туслах.

ЗОРИЛГО:
Доорх мэдээлэлд үндэслэн өндөр чанартай, логиктой, мэргэжлийн, академик түвшиний хариулт өгөх.
Хүний нөөцийн менежерүүд, central test ашиглаж буй байгууллага хувь хүмүүст зориулах
Монгол хэлээр утга зүйн алдаагүй, үг үсэг дүрмийн алдаагүй байх

ДҮРЭМ:
1. Зөвхөн доорх мэдээлэлд тулгуурлана
2. Өөрөөсөө зохиох, болон өөр open source мэдээлэл ашиглаж болохгүй
3. Хэрэв мэдээлэл байхгүй бол: "Мэдээлэл алга"
4. Хариултыг:
   - Эхлээд товч
   - Дараа нь дэлгэрэнгүй тайлбар
   - Хэрэв боломжтой бол bullet point ашигла
5. Монгол хэлээр, маш ойлгомжтой бич
                f"Дараах мэдээлэлд тулгуурлан хэрэглэгчийн асуултад маш тодорхой хариулна уу.\n\n"
                f"Дараах мэдээлэлд үндэслэн өндөр чанартай, логиктой, мэргэжлийн, академик түвшиний, хариулт өгөх"
                f"Хүний нөөцийн менежерүүд,  central test ашиглаж буй байгууллага хувь хүмүүст зориулах"
                f"Монгол хэлээр үг үсэг, утга зүй, зөв бичгийн дүрмийн алдаагүй, найруулга маш сайн хариулт өгөх"
                f"Зөвхөн дараах мэдээлэлд үндэслэж хариулт өгнө, өөрөөсөө зохиох болон өөр эх сурвалж ашиглахгүй"
                f"Хэрэв мэдээлэл байхгүй бол Мэдээлэл алга гэж хариулна"
                f"Эхлээд товч, дараа нь дэлгэргүй байдлаар хариулт өгөх"
                f"Хариулт бичихээсээ өмнө өөрийн гаргасан дүгнэлт бүрийг өгөгдсөн текст дэх баримттай тулгаж, энэ мэдээлэл эх сурвалжад үнэхээр байгаа юу гэж асуунга. Баримтаар нотлогдохгүй бол хариултаас хас"
                f"Хүний нөөцийн салбарын нэр томьёог ашиглах"
                f"Хариултаа бичсэнийхээ дараа өөрөө дахин уншиж, утга давтагдсан эсвэл академик бус үг хэллэг байгаа эсэхийг шалгаж, засаж сайжруулсны дараа эцсийн хувилбарыг гарга"
                f"Холбогдох мэдээлэл: {context_text}\n\n"
                f"Хэрэглэгчийн асуулт: {query}"
            )
            
            print("Gemini хариулж байна...")
            response = genai_client.models.generate_content_stream(
                model="gemini-2.5-flash",
                contents=prompt
            )
            
            for chunk in response:
                chunk_text = getattr(chunk, "text", "")
                if chunk_text:
                    # Frontend-рүү датаг JSON форматаар илгээх
                    await websocket.send_text(json.dumps({
                        "content": chunk_text,
                        "type": "chunk"
                    }))
            
            # Хариулт дууссаныг мэдэгдэх
            await websocket.send_text(json.dumps({"type": "done"}))
            print("Хариулт амжилттай илгээгдэж дууслаа.")

    except WebSocketDisconnect:
        print("Хэрэглэгч саллаа")
    except Exception as e:
        print(f"Гэнэтийн алдаа: {e}")
    finally:
        if not websocket.client_state.name == 'DISCONNECTED':
            await websocket.close()

if __name__ == "__main__":
    import uvicorn
    # 5000 порт дээр ажиллуулна
    uvicorn.run(app, host="0.0.0.0", port=5000)