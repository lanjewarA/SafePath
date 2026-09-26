"use client";

import { useState } from "react";
import { MessageSquare, Send, Bot, User, Loader2, Sparkles } from "lucide-react";

interface Message {
  sender: "user" | "copilot";
  text: string;
  engine?: string;
}

export default function ChatPage() {
  const [query, setQuery] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      sender: "copilot",
      text: "Hello! I am your SafePath AI Safety Copilot. Ask me anything about calculated route safety scores, lighting conditions, GNN risk predictions, or safe walking detours across Mumbai / West India.",
      engine: "Gemini LLM + ChromaDB RAG Engine"
    },
  ]);

  const handleSend = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!query.trim() || loading) return;

    const userText = query.trim();
    setQuery("");
    setMessages((prev) => [...prev, { sender: "user", text: userText }]);
    setLoading(true);

    try {
      const res = await fetch("http://localhost:8000/api/chat/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_query: userText }),
      });

      if (!res.ok) throw new Error(`HTTP Error ${res.status}`);

      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        {
          sender: "copilot",
          text: data.answer,
          engine: data.engine,
        },
      ]);
    } catch (err: any) {
      console.error("Copilot chat error:", err);
      setMessages((prev) => [
        ...prev,
        {
          sender: "copilot",
          text: "Sorry, I had trouble contacting the safety database. Please ensure the backend server is running on port 8000.",
          engine: "Error Fallback",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto w-full p-6 flex flex-col flex-1 gap-4 h-[calc(100vh-90px)]">
      <div className="bg-slate-800 p-4 rounded-lg border border-slate-700 shadow-xl flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <Bot className="w-6 h-6 text-purple-400" />
            Safety Copilot (RAG Assistant)
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Explains route safety factors, GNN spatial risk modeling, and lighting levels. Grounded in Gemini LLM + ChromaDB.
          </p>
        </div>
      </div>

      {/* Quick Questions */}
      <div className="flex flex-wrap gap-2 text-xs">
        <span className="text-[10px] text-slate-400 font-semibold w-full">Quick Questions:</span>
        <button
          onClick={() => { setQuery("Why is Route B recommended over Route A?"); }}
          className="bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 px-2.5 py-1 rounded"
        >
          Why is Route B recommended?
        </button>
        <button
          onClick={() => { setQuery("Why is Senapati Bapat Marg flagged high risk at 10 PM?"); }}
          className="bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 px-2.5 py-1 rounded"
        >
          Senapati Bapat Marg risk?
        </button>
        <button
          onClick={() => { setQuery("Which route has the best CCTV density and lighting?"); }}
          className="bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 px-2.5 py-1 rounded"
        >
          Best lighting & CCTV route?
        </button>
      </div>

      {/* Chat Messages Window */}
      <div className="flex-1 bg-slate-800/60 rounded-lg border border-slate-700 p-4 flex flex-col gap-4 overflow-y-auto min-h-[350px]">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex flex-col max-w-xl text-sm ${
              msg.sender === "user"
                ? "self-end bg-purple-900/70 border border-purple-700 text-purple-100 rounded-2xl rounded-tr-none p-3.5"
                : "self-start bg-slate-900 border border-slate-700 text-slate-200 rounded-2xl rounded-tl-none p-4 shadow-lg"
            }`}
          >
            <div className="flex items-center gap-1.5 font-semibold text-xs mb-1.5">
              {msg.sender === "user" ? (
                <>
                  <User className="w-3.5 h-3.5 text-purple-300" />
                  <span className="text-purple-300">You</span>
                </>
              ) : (
                <>
                  <Bot className="w-4 h-4 text-purple-400" />
                  <span className="text-purple-400">Safety Copilot</span>
                  {msg.engine && (
                    <span className="ml-auto text-[10px] font-mono text-slate-400 bg-slate-800 px-2 py-0.5 rounded border border-slate-700">
                      {msg.engine}
                    </span>
                  )}
                </>
              )}
            </div>

            <div className="whitespace-pre-line leading-relaxed text-xs md:text-sm">
              {msg.text}
            </div>
          </div>
        ))}

        {loading && (
          <div className="self-start bg-slate-900 border border-slate-700 text-slate-400 rounded-2xl rounded-tl-none p-3 flex items-center gap-2 text-xs">
            <Loader2 className="w-4 h-4 animate-spin text-purple-400" />
            <span>Retrieving safety database context & generating answer...</span>
          </div>
        )}
      </div>

      {/* Input Box */}
      <form onSubmit={handleSend} className="flex items-center gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask a question about route safety, lighting, or GNN spatial risk..."
          className="flex-1 bg-slate-800 border border-slate-700 rounded-lg p-3 text-sm text-slate-100 focus:outline-none focus:border-purple-500"
        />
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="bg-purple-600 hover:bg-purple-500 disabled:bg-purple-900 text-white font-medium p-3 rounded-lg flex items-center justify-center transition-colors shadow-lg"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
}


