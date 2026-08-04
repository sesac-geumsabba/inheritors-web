'use client';

import React, { useState } from 'react';
import { QuickButtons, DocumentCard } from '../components/QuickButtons';
import { DocumentCardList } from '../components/DocumentCardList';
import { LawSourceCard, LawSourceItem } from '../components/LawSourceCard';
import './chatbot.css';

interface Message {
  id: string;
  sender: 'user' | 'bot';
  text: string;
  sources?: LawSourceItem[];
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      sender: 'bot',
      text: '안녕하세요! 유언대용신탁 자산승계 설계 챗봇입니다. 아래 Quick 버튼을 누르시거나 궁하신 판례 및 법령 질문을 입력해주세요.',
    },
  ]);
  const [input, setInput] = useState('');
  const [documents, setDocuments] = useState<DocumentCard[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const handleSelectPreset = (presetQuery: string, docs: DocumentCard[]) => {
    const userMsgId = Date.now().toString();
    const botMsgId = (Date.now() + 1).toString();

    setMessages((prev) => [
      ...prev,
      { id: userMsgId, sender: 'user', text: presetQuery },
      {
        id: botMsgId,
        sender: 'bot',
        text: `[Quick 추천 응답] "${presetQuery}" 에 관한 추천 법률/판례 및 사례 자료입니다.`,
      },
    ]);
    setDocuments(docs);
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userQuery = input.trim();
    const userMsgId = Date.now().toString();
    
    setMessages((prev) => [
      ...prev,
      { id: userMsgId, sender: 'user', text: userQuery },
    ]);
    setInput('');
    setIsLoading(true);

    try {
      const apiHost = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const res = await fetch(`${apiHost}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userQuery }),
      });

      if (!res.ok) {
        throw new Error(`HTTP error: ${res.status}`);
      }

      const data = await res.json();
      const botMsgId = (Date.now() + 1).toString();

      setMessages((prev) => [
        ...prev,
        {
          id: botMsgId,
          sender: 'bot',
          text: data.answer,
          sources: data.sources || [],
        },
      ]);
    } catch (err) {
      console.error('Chat error:', err);
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          sender: 'bot',
          text: '응답 생성 중 오류가 발생했습니다. 백엔드 연결 상태를 확인해 주세요.',
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="chat-container">
      <header className="chat-header">
        <h2>🏛️ 유언대용신탁 자산승계 설계 챗봇</h2>
      </header>

      <QuickButtons
        onSelectPreset={handleSelectPreset}
        isLoading={isLoading}
        setIsLoading={setIsLoading}
      />

      <div className="chat-messages-box">
        {messages.map((msg) => (
          <div key={msg.id} className="chat-message-group">
            <div className={`chat-bubble ${msg.sender}`}>
              {msg.text}
            </div>

            {/* 법령 및 판례 MCP 출처 카드 바인딩 */}
            {msg.sender === 'bot' && msg.sources && msg.sources.length > 0 && (
              <div className="mcp-sources-container mt-2 w-full space-y-2">
                <p className="text-xs font-bold text-gray-500">📌 관련 법률/판례 출처 카드</p>
                {msg.sources.map((src, idx) => (
                  <LawSourceCard key={idx} source={src} />
                ))}
              </div>
            )}
          </div>
        ))}

        <DocumentCardList documents={documents} isLoading={isLoading} />
      </div>

      <form onSubmit={handleSend} className="chat-input-form">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="판례나 법령 질문을 입력하세요 (예: 유언대용신탁 판례)"
          className="chat-input"
          disabled={isLoading}
        />
        <button type="submit" disabled={isLoading || !input.trim()} className="chat-send-btn">
          전송
        </button>
      </form>
    </main>
  );
}
