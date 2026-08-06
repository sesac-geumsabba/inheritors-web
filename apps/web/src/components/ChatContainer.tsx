"use client";

import React, { useState } from "react";
import { LawSourceCard, LawSourceItem } from "./LawSourceCard";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: LawSourceItem[];
}

export const ChatContainer: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "안녕하세요! 상속 및 유언대용신탁 관련 법령과 대법원 판례를 자유롭게 물어보세요.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userText = input.trim();
    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: userText,
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const apiHost = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${apiHost}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userText }),
      });

      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }

      const data = await res.json();
      const aiMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: data.answer,
        sources: data.sources || [],
      };

      setMessages((prev) => [...prev, aiMsg]);
    } catch (err) {
      console.error("Chat API call error:", err);
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: "죄송합니다. 백엔드 연결 중 오류가 발생했습니다.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] max-w-3xl mx-auto p-4 bg-white dark:bg-gray-900 rounded-xl shadow-md border border-gray-200 dark:border-gray-800">
      {/* Header */}
      <div className="pb-3 mb-3 border-b border-gray-200 dark:border-gray-800">
        <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">
          ⚖️ 유언대용신탁 & 법률 RAG 챗봇
        </h2>
        <p className="text-xs text-gray-500">
          실시간 대한민국 법제처 DB & 대법원 판례 연동
        </p>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto space-y-4 pr-1">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex flex-col ${
              msg.role === "user" ? "items-end" : "items-start"
            }`}
          >
            <div
              className={`p-3.5 rounded-2xl max-w-xl text-sm leading-relaxed ${
                msg.role === "user"
                  ? "bg-blue-600 text-white rounded-br-none"
                  : "bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-bl-none border border-gray-200 dark:border-gray-700"
              }`}
            >
              {msg.content}
            </div>

            {/* MCP Law Source Cards */}
            {msg.role === "assistant" && msg.sources && msg.sources.length > 0 && (
              <div className="mt-3 w-full max-w-xl space-y-2">
                <p className="text-xs font-bold text-gray-500 dark:text-gray-400">
                  📌 관련 법률 및 판례 출처 ({msg.sources.length}건)
                </p>
                {msg.sources.map((src, idx) => (
                  <LawSourceCard key={idx} source={src} />
                ))}
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="flex items-start">
            <div className="p-3 bg-gray-100 dark:bg-gray-800 rounded-2xl text-xs text-gray-500 animate-pulse">
              법제처 및 대법원 판례 DB에서 관련 조문을 조율 중입니다...
            </div>
          </div>
        )}
      </div>

      {/* Input Form */}
      <div className="pt-3 mt-3 border-t border-gray-200 dark:border-gray-800 flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="판례나 법령 질문을 입력하세요 (예: 유언대용신탁 판례)"
          className="flex-1 px-4 py-2.5 text-sm border rounded-xl bg-gray-50 dark:bg-gray-800 border-gray-300 dark:border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900 dark:text-gray-100"
        />
        <button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          className="px-5 py-2.5 text-sm font-semibold bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-xl transition"
        >
          전송
        </button>
      </div>
    </div>
  );
};

export default ChatContainer;
