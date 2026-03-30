import os
import json
import asyncio
import sys
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai  # Илүү тогтвортой сан
from pinecone import Pinecone
from dotenv import load_dotenv

# .env файлаас нууц түлхүүрүүдийг унших
load_dotenv(override=True)

# Windows консол дээр Монгол үсэг алдаагүй гаргах
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
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

# Gemini тохиргоо
genai.configure(api_key=GOOGLE_API_KEY)

# Pinecone тохиргоо
pc = Pinecone(api_key=PINECONE_API_KEY)
index_name = "testai"
index = pc.Index(index_name)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("--- Central Test AI: Шинэ хэрэглэгч холбогдлоо ---")
    
    try:
        while True:
            # 1. Хэрэглэгчээс дата хүлээж авах
            raw_data = await websocket.receive_text()
            try:
                data_json = json.loads(raw_data)
                query = data_json.get("message", raw_data)
            except json.JSONDecodeError:
                query = raw_data

            print(f"Асуулт: {query}")

            # 2. Pinecone-оос хайх (Embedding + Retrieval)
            context_text = ""
            try:
                # Embedding үүсгэх
                embed_res = genai.embed_content(
                    model="models/embedding-001",
                    content=query,
                    task_type="retrieval_query"
                )
                query_vector = embed_res['embedding']
                
                # Pinecone-оос хайх
                search_results = index.query(vector=query_vector, top_k=3, include_metadata=True)
                
                contexts = []
                for match in search_results["matches"]:
                    if "text" in match["metadata"]:
                        contexts.append(match["metadata"]["text"])
                
                context_text = "\n".join(contexts) if contexts else "Мэдээлэл олдсонгүй."
            except Exception as e:
                print(f"Retrieval алдаа: {e}")
                context_text = "Мэдээллийн сантай холбогдоход алдаа гарлаа."

            # 3. Ухаалаг Prompt болон Gemini Generation
            # ЧУХАЛ: Заавал gemini-1.5-flash эсвэл gemini-2.0-flash-exp ашиглана
            model = genai.GenerativeModel("gemini-2.5-flash")
            
            prompt = (
                f"Чи бол Central Test компанийн албан ёсны зөвлөх AI туслах байна.\n\n"
                f"ЗОРИЛГО:\n"
                f"Хүний нөөцийн менежерүүдэд зориулсан академик түвшний, мэргэжлийн хариулт өгөх.\n\n"
                f"ДҮРЭМ:\n"
                f"3. Хариултыг эхлээд ТОВЧ, дараа нь ДЭЛГЭРЭНГҮЙ тайлбарлан бич.\n"
                f"4. Психометрик болон Хүний нөөцийн нэр томьёог зөв ашигла.\n"
                f"5. Найруулга зүй болон зөв бичгийн дүрмийн алдаагүй байх.\n\n"
                f"CONTEXT (Мэдээллийн сан):\n{context_text}\n\n"
                f"ХЭРЭГЛЭГЧИЙН АСУУЛТ: {query}\n\n"
                f"ХАРИУЛТ:"
            )

            print("Gemini хариулж байна...")
            try:
                # Streaming ашиглан хариулт илгээх
                response = model.generate_content(prompt, stream=True)
                
                for chunk in response:
                    if chunk.text:
                        await websocket.send_text(json.dumps({
                            "content": chunk.text,
                            "type": "chunk"
                        }))
                
                await websocket.send_text(json.dumps({"type": "done"}))
                print("Хариулт дууслаа.")
            except Exception as e:
                print(f"Gemini алдаа: {e}")
                await websocket.send_text(json.dumps({"content": f"Алдаа гарлаа: {str(e)}", "type": "error"}))

    except WebSocketDisconnect:
        print("Хэрэглэгч саллаа.")
    except Exception as e:
        print(f"Системийн алдаа: {e}")
    finally:
        try:
            await websocket.close()
        except:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)