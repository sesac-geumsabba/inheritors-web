'use client';

import React, { useState } from 'react';
import { QuickButtons, DocumentCard } from '../components/QuickButtons';
import { DocumentCardList } from '../components/DocumentCardList';
import './chatbot.css';

interface Message {
  id: string;
  sender: 'user' | 'bot';
  text: string;
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      sender: 'bot',
      text: '안녕하세요! 유언대용신탁 자산승계 설계 챗봇입니다. 아래 Quick 버튼을 누르시거나 궁금하신 질문을 입력해주세요.',
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

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMsgId = Date.now().toString();
    setMessages((prev) => [
      ...prev,
      { id: userMsgId, sender: 'user', text: input },
    ]);
    setInput('');
    // 일반 질의 전송 시 기존 Quick 문서는 초기화
    setDocuments([]);
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
          <div key={msg.id} className={`chat-bubble ${msg.sender}`}>
            {msg.text}
          </div>
        ))}

        <DocumentCardList documents={documents} isLoading={isLoading} />
      </div>

      <form onSubmit={handleSend} className="chat-input-form">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="질문을 입력하세요..."
          className="chat-input"
          disabled={isLoading}
        />
        <button type="submit" disabled={isLoading} className="chat-send-btn">
          전송
        </button>
      </form>
    </main>
  );
}
