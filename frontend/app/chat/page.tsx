"use client";

import { MessageSquare, Send, Bot } from "lucide-react";

export default function ChatPage() {
  return (
    <div className="max-w-4xl mx-auto w-full p-6 flex flex-col flex-1 gap-4">
      <div className="bg-slate-800 p-4 rounded-lg border border-slate-700 shadow-xl flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <Bot className="w-6 h-6 text-purple-400" />
            Safety Copilot (RAG Assistant)
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Ask questions about route risk scores, lighting levels, or detour recommendations. Grounded in Gemini LLM + ChromaDB vector database.
          </p>
        </div>
      </div>

      {/* Chat Messages Window */}
      <div className="flex-1 bg-slate-800/60 rounded-lg border border-slate-700 p-4 flex flex-col gap-4 overflow-y-auto min-h-[350px]">
        <div className="bg-slate-900 border border-slate-700 p-3 rounded.lg max-w-md self-start text-sm text-slate-200">
          <div className="flex items-center gap-1.5 font-semibold text-purple-400 mb-1 text-xs">
            <Bot className="w-3.5 h-3.5" /> Safety Copilot
          </div>
          Hello! Ask me anything about safety scores, lighting conditions, or safest walking routes across Mumbai / West India.
        </div>
      </div>

      {/* Input Box */}
      <form onSubmit={(e) => e.preventDefault()} className="flex items-center gap-2">
        <input
          type="text"
          placeholder="e.g. Why is the route via Senapati Bapat Marg flagged high risk at 10 PM?"
          className="flex-1 bg-slate-800 border border-slate-700 rounded-lg p-3 text-sm text-slate-100 focus:outline-none focus:border-purple-500"
        />
        <button className="bg-purple-600 hover:bg-purple-500 text-white font-medium p-3 rounded-lg flex items-center justify-center gap-2 transition-colors shadow-lg">
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
}

