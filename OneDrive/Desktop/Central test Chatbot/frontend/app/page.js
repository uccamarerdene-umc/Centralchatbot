"use client";

import { useEffect, useRef, useState } from "react";
import { Send } from "lucide-react";

const WS_URL = "ws://localhost:5000/ws";

export default function HomePage() {
  const socketRef = useRef(null);
  const reconnectTimerRef = useRef(null);
  const shouldReconnectRef = useRef(true);
  const [isConnected, setIsConnected] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: "Сайн байна уу, танд юугаар туслах вэ?",
      isStreaming: false,
    },
  ]);

  useEffect(() => {
    connectSocket();

    return () => {
      shouldReconnectRef.current = false;
      clearTimeout(reconnectTimerRef.current);
      socketRef.current?.close();
    };
  }, []);

  const connectSocket = () => {
    clearTimeout(reconnectTimerRef.current);

    const ws = new WebSocket(WS_URL);
    socketRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
    };

    ws.onclose = () => {
      setIsConnected(false);
      setIsSending(false);
      if (shouldReconnectRef.current) {
        reconnectTimerRef.current = setTimeout(connectSocket, 1500);
      }
    };

    ws.onerror = () => {
      ws.close();
    };

    ws.onmessage = (event) => {
      handleIncomingMessage(event.data);
    };
  };

  const handleIncomingMessage = (rawData) => {
    let parsed;
    try {
      parsed = JSON.parse(rawData);
    } catch {
      appendChunk(String(rawData));
      return;
    }

    if (parsed?.text === "chunk") {
      appendChunk(parsed.chunk ?? parsed.content ?? "");
      return;
    }

    if (parsed?.type === "done") {
      setIsSending(false);
      finishStreamingMessage();
      return;
    }

    if (parsed?.type === "error") {
      setIsSending(false);
      appendChunk(`\n[Алдаа]: ${parsed.message ?? "Unknown error"}`);
      finishStreamingMessage();
      return;
    }

    if (typeof parsed?.content === "string") {
      appendChunk(parsed.content);
    }
  };

  const appendChunk = (chunkText) => {
    if (!chunkText) return;

    setMessages((prev) => {
      const next = [...prev];
      const last = next[next.length - 1];

      if (last && last.role === "assistant" && last.isStreaming) {
        last.content += chunkText;
      } else {
        next.push({
          role: "assistant",
          content: chunkText,
          isStreaming: true,
        });
      }

      return next;
    });
  };

  const finishStreamingMessage = () => {
    setMessages((prev) =>
      prev.map((msg, idx) =>
        idx === prev.length - 1 && msg.role === "assistant"
          ? { ...msg, isStreaming: false }
          : msg
      )
    );
  };

  const handleSend = () => {
    const trimmed = input.trim();
    const ws = socketRef.current;

    if (!trimmed || !ws || ws.readyState !== WebSocket.OPEN || isSending) return;

    setMessages((prev) => [
      ...prev,
      { role: "user", content: trimmed, isStreaming: false },
    ]);
    setInput("");
    setIsSending(true);
    ws.send(JSON.stringify({ message: trimmed }));
  };

  return (
    <main className="flex min-h-screen w-full items-center justify-center bg-background px-4 py-6">
      <section className="flex h-[85vh] w-full max-w-3xl flex-col overflow-hidden rounded-xl border border-[#e5e7eb] bg-card shadow-sm">
        <header className="border-b border-[#e5e7eb] px-5 py-4">
          <h1 className="text-[20px] font-semibold text-foreground">AI Chatbot</h1>
          <p className="mt-1 text-[14px] text-muted-foreground">
            Status: {isConnected ? "Connected" : "Reconnecting..."}
          </p>
        </header>

        <div className="flex-1 space-y-3 overflow-y-auto bg-[#f8fafc] p-4">
          {messages.map((msg, idx) => (
            <div
              key={`${msg.role}-${idx}`}
              className={`max-w-[85%] rounded-lg px-4 py-3 text-[14px] leading-6 ${
                msg.role === "user"
                  ? "ml-auto bg-[#030213] text-white"
                  : "bg-white text-[#111827] shadow-sm"
              }`}
            >
              {msg.content}
              {msg.role === "assistant" && msg.isStreaming ? (
                <span className="ml-1 inline-block animate-pulse">|</span>
              ) : null}
            </div>
          ))}
        </div>

        <footer className="border-t border-[#e5e7eb] bg-white p-4">
          <div className="flex items-center gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSend();
              }}
              placeholder="Мессежээ бичнэ үү..."
              className="h-11 flex-1 rounded-lg border border-[#d1d5db] bg-white px-3 text-[14px] text-foreground outline-none transition focus:border-[#030213] focus:ring-2 focus:ring-[#030213]/15"
            />
            <button
              type="button"
              onClick={handleSend}
              disabled={!isConnected || isSending || !input.trim()}
              className="inline-flex h-11 items-center gap-2 rounded-lg bg-[#030213] px-4 text-[14px] font-medium text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Send size={16} />
              Send
            </button>
          </div>
        </footer>
      </section>
    </main>
  );
}
