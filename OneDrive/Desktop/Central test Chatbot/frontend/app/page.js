"use client";
import { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import { PlusCircle, History, HelpCircle, ArrowRightCircle, MessageSquare, Lightbulb } from "lucide-react";

export default function ChatPage() {
  const [input, setInput] = useState("");
  const [chats, setChats] = useState([]); 
  const [currentChatId, setCurrentChatId] = useState(null); 
  const [isLoading, setIsLoading] = useState(false);
  const responseEndRef = useRef(null);
  const socketRef = useRef(null);

  // 1. LocalStorage-оос дата унших
  useEffect(() => {
    try {
      const saved = localStorage.getItem("central_test_history");
      if (saved) {
        const parsedChats = JSON.parse(saved);
        setChats(parsedChats);
        if (parsedChats.length > 0) setCurrentChatId(parsedChats[0].id);
      }
    } catch (e) {
      console.error("LocalStorage-оос уншихад алдаа:", e);
    }
  }, []);

  // 2. LocalStorage руу хадгалах
  useEffect(() => {
    if (chats.length > 0) {
      localStorage.setItem("central_test_history", JSON.stringify(chats));
    }
  }, [chats]);

  useEffect(() => {
    responseEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chats, currentChatId]);

  const createNewChat = () => {
    const newChat = {
      id: Date.now().toString(),
      title: "Шинэ яриа " + (chats.length + 1),
      messages: []
    };
    setChats([newChat, ...chats]);
    setCurrentChatId(newChat.id);
  };

  const currentChat = chats.find(c => c.id === currentChatId);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    let chatId = currentChatId;
    if (!chatId) {
      const newChat = {
        id: Date.now().toString(),
        title: input.substring(0, 30) + "...",
        messages: []
      };
      setChats([newChat, ...chats]);
      setCurrentChatId(newChat.id);
      chatId = newChat.id;
    }

    const userMessage = input;
    setInput("");
    setIsLoading(true);

    updateChatMessages(chatId, { role: "user", content: userMessage });

    const socket = new WebSocket("ws://localhost:8000/ws");
    socketRef.current = socket;
    let assistantResponse = "";

    socket.onopen = () => {
      socket.send(JSON.stringify({ message: userMessage }));
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "chunk") {
          assistantResponse += data.content;
          updateChatMessages(chatId, { role: "assistant", content: assistantResponse }, true);
        } else if (data.type === "done") {
          setIsLoading(false);
          socket.close();
        }
      } catch (err) {}
    };

    socket.onerror = () => {
      updateChatMessages(chatId, { role: "assistant", content: "Холболтын алдаа гарлаа." });
      setIsLoading(false);
    };
  };

  const updateChatMessages = (chatId, newMessage, isStreaming = false) => {
    setChats(prevChats => prevChats.map(chat => {
      if (chat.id === chatId) {
        let newMessages = [...chat.messages];
        if (isStreaming && newMessages.length > 0 && newMessages[newMessages.length - 1].role === "assistant") {
          newMessages[newMessages.length - 1].content = newMessage.content;
        } else {
          newMessages.push(newMessage);
        }
        
        let newTitle = chat.title;
        if (!isStreaming && newMessage.role === "user" && chat.messages.length === 0) {
            newTitle = newMessage.content.substring(0, 30) + "...";
        }
        
        return { ...chat, messages: newMessages, title: newTitle };
      }
      return chat;
    }));
  };

  return (
    <div className="flex h-screen bg-white text-gray-800 overflow-hidden font-sans">
      
      {/* --- LEFT SIDEBAR --- */}
      <aside className="w-72 border-r border-gray-100 flex flex-col p-6 bg-gray-50/50">
        <h1 className="text-xl font-bold mb-8 text-gray-900 tracking-tight">Central Test AI</h1>
        <button onClick={createNewChat} className="flex items-center justify-center gap-2 bg-purple-600 hover:bg-purple-700 text-white py-3 px-4 rounded-xl font-medium mb-10 transition-all text-sm shadow-sm active:scale-95">
          <PlusCircle size={18} /> Шинэ яриа эхлүүлэх
        </button>
        <div className="flex-1 overflow-y-auto">
          <div className="flex items-center gap-2 text-gray-400 mb-4 px-2 italic text-xs uppercase tracking-widest font-bold">
            <History size={14} /> Research History
          </div>
          <div className="space-y-1.5">
            {chats.map((chat) => (
              <div key={chat.id} onClick={() => setCurrentChatId(chat.id)} className={`group p-3 rounded-xl border transition-all duration-300 cursor-pointer ${currentChatId === chat.id ? "bg-purple-100 border-purple-200" : "bg-transparent border-transparent hover:bg-white hover:border-gray-100"}`}>
                <div className="flex items-center gap-2">
                  <MessageSquare size={14} className={currentChatId === chat.id ? "text-purple-600" : "text-gray-400"} />
                  <p className={`text-sm truncate ${currentChatId === chat.id ? "text-purple-800 font-bold" : "text-gray-600 group-hover:text-purple-700"}`}>{chat.title}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </aside>

      {/* --- MAIN CHAT AREA --- */}
      <main className="flex-1 flex flex-col relative bg-white">
        <div className="max-w-4xl w-full mx-auto flex flex-col h-full p-10">
          <div className="mb-8 z-10">
            <p className="text-[10px] text-gray-400 uppercase tracking-[0.2em] mb-3 font-bold">Ask Central Test AI...</p>
            <form onSubmit={handleSubmit} className="relative">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Асуултаа энд бичнэ үү..."
                className="w-full p-4 bg-gray-50 border border-gray-200 rounded-2xl focus:ring-2 focus:ring-purple-500 outline-none text-base transition-all pr-14 shadow-sm"
                disabled={isLoading}
              />
              <button type="submit" disabled={isLoading || !input.trim()} className={`absolute right-3 top-1/2 -translate-y-1/2 p-2.5 rounded-full transition-all ${isLoading ? 'bg-gray-200' : 'bg-purple-600 hover:bg-purple-700'} text-white`}>
                <ArrowRightCircle size={22} strokeWidth={2.5} />
              </button>
            </form>
          </div>

          <div className="flex-1 overflow-y-auto pr-4 mb-6">
            {currentChat && currentChat.messages.length > 0 ? (
              <div className="space-y-6">
                {currentChat.messages.map((msg, idx) => (
                  <div key={idx} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                    <div className={`max-w-[80%] p-4 rounded-2xl ${msg.role === "user" ? "bg-gray-100 text-gray-800" : "bg-purple-50/50 border border-purple-100 text-gray-700 prose prose-purple prose-sm max-w-none"}`}>
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  </div>
                ))}
                <div ref={responseEndRef} className="h-4" />
              </div>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-gray-300 opacity-40">
                <HelpCircle size={48} className="mb-4" />
                <p>Асуултаа бичээд яриаг эхлүүлээрэй</p>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* --- RIGHT INFO PANEL --- */}
      <aside className="w-[420px] p-8 border-l border-gray-50 hidden xl:block bg-white overflow-y-auto">
        <div className="sticky top-0 space-y-10">
          <div>
            <h3 className="text-2xl font-black mb-8 leading-tight text-gray-900">Хэрхэн ашиглах вэ?</h3>
            <div className="space-y-6">
              <div className="bg-purple-50 p-7 rounded-3xl border border-purple-100 shadow-sm flex items-start gap-5 transition-transform hover:scale-[1.02]">
                <div className="bg-purple-600 p-2.5 rounded-2xl text-white shadow-md">
                  <Lightbulb size={28} />
                </div>
                <div>
                  <p className="text-xs font-black text-purple-700 mb-2 uppercase tracking-wider">Зөвлөмж</p>
                  <p className="text-[15px] text-purple-950 font-medium leading-relaxed">Психометрик тестийн үр дүнг хэрэглээнд нэвтрүүлэх болон тайлан унших талаар асууж болно.</p>
                </div>
              </div>
              <div className="p-7 rounded-3xl border border-gray-100 bg-gray-50/30">
                <p className="text-[14px] text-gray-500 italic border-l-4 border-purple-200 pl-4 leading-relaxed">
                  Жишээ нь: <span className="font-semibold text-gray-700">"Big Five тестийн давуу тал юу вэ?"</span>
                </p>
              </div>
            </div>
          </div>
          
          <div className="border-t border-gray-100 pt-10 text-center">
            <div className="p-6 rounded-3xl bg-gradient-to-b from-gray-50 to-white border border-gray-100">
              <div className="w-16 h-16 bg-white rounded-2xl shadow-sm border flex items-center justify-center mx-auto mb-5">
                <HelpCircle size={32} className="text-purple-500 opacity-80" />
              </div>
              <p className="text-base font-bold text-gray-800 mb-2">Тусламж хэрэгтэй юу?</p>
              <p className="text-sm text-gray-500 mb-5">Мэргэжлийн зөвлөгөө аваарай.</p>
              <button className="w-full py-3 bg-white border border-purple-200 text-purple-700 font-bold text-sm rounded-xl hover:bg-purple-50 transition-all shadow-sm">Бидэнтэй холбогдох</button>
            </div>
          </div>
        </div>
      </aside>
    </div>
  );
}