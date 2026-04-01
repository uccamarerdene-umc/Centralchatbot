import os
import json
import asyncio
import sys
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types as genai_types
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

# Gemini клиент (generate_content_stream, embed_content)
gemini_client = genai.Client(api_key=GOOGLE_API_KEY)

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
                # IMPORTANT:
                # Your Gemini API setup may not support `models/embedding-001` for `embedContent`.
                # Use the same embedding model as `ingest.py` to keep vector dimensions consistent.
                embed_model_candidates = [
                    "models/gemini-embedding-001",
                    "models/embedding-001",  # fallback for older/alternate configs
                ]
                embed_res = None
                last_embed_err = None
                for embed_model in embed_model_candidates:
                    try:
                        embed_res = gemini_client.models.embed_content(
                            model=embed_model,
                            contents=query,
                            config=genai_types.EmbedContentConfig(
                                task_type="RETRIEVAL_QUERY",
                            ),
                        )
                        break
                    except Exception as e:
                        # If the API key is invalid/rejected, fallbacks will just hide the real root cause.
                        msg = str(e).lower()
                        if "403" in msg or "leaked" in msg:
                            raise
                        last_embed_err = e

                if embed_res is None:
                    raise RuntimeError(
                        f"Embedding failed for all candidate models. Last error: {last_embed_err}"
                    )

                query_vector = embed_res.embeddings[0].values
                
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

            # 3. Ухаалаг Prompt болон Gemini Generation (generate_content_stream)
            prompt = (
                f"Чи бол Central Test компанийн албан ёсны AI зөвлөх байна.\n\n"
                f"ЗОРИЛГО:\n"
                f"Хүний нөөцийн менежерүүдэд зориулсан академик түвшний, мэргэжлийн хариулт өгөх.\n\n"
                f"ДҮРЭМ:\n"
                f"3. Хариултыг ДЭЛГЭРЭНГҮЙ тайлбарлан бич.'Одоор тэмдэглэсэн' гарчиг, тэмдэглэгээг ТЕКСТЭНД ХЭЗЭЭ Ч БИТГИ АШИГЛА.\n"
                f"4. Сэтгэл зүйн шинжлэх ухааны болон Хүний нөөцийн нэр томьёог зөв ашигла.\n"
                f"5. Найруулга зүй болон зөв бичгийн дүрмийн алдаагүй байх.\n\n"
                f"6. Хариултын хамгийн чухал нэр томьёо, түлхүүр өгүүлбэрүүдийг заавал **Bold** болгож бич"
                f"CONTEXT (Мэдээллийн сан):\n{context_text}\n\n"
                f"ХЭРЭГЛЭГЧИЙН АСУУЛТ: {query}\n\n"
                f"ХАРИУЛТ:"
            )

            print("Gemini хариулж байна...")
            try:
                response = gemini_client.models.generate_content_stream(
                    model="gemini-2.5-flash",
                    contents=prompt,
                )
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
    uvicorn.run(app, host="0.0.0.0", port=8000)