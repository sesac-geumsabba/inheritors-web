"use client";

import { useEffect, useRef, useState } from "react";
import TopAppBar from "@/components/TopAppBar";
import BottomNavBar from "@/components/BottomNavBar";

interface ChatSource {
  source_type: "internal_chunk" | "case_law" | "statute";
  title: string;
  page: number | null;
  url: string | null;
  score: number;
  snippet: string;
}

const SOURCE_ICON: Record<ChatSource["source_type"], string> = {
  internal_chunk: "description",
  case_law: "gavel",
  statute: "menu_book",
};

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: ChatSource[];
  awaitingContinueId?: number;
}

const DISCLAIMER =
  "본 내용은 정보 제공을 목적으로 작성되었으며, 정확한 내용 및 적용 여부는 반드시 전문가와 상담하시기 바랍니다.";

const NEURI_AVATAR =
  "https://lh3.googleusercontent.com/aida-public/AB6AXuCrGft8CohQhylCbrlOxpU4hyhorNkMh8IQq8NxSvNlLSJLJb-CRcCuFoMz4mgRkjxUwcMgHfpqYgiBT3xItUBUYKwglnqpz7heps2jgoW_so6cVh76TQ1zKRWIzKK0outyWnb1eMp_2Ij8ymT8U2TfAOdnMqMu4B29Md7XV4kCL3DyiXQgvqql547UHwBIuf6BYv9CIptAzYZ1WF3GNNL6HEVbyhxBvJX5ZU98fAqkap0KLLB3DwFlohkLPOiCbcpqxvY";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "안녕하세요! 상속자들의 법률 도우미 챗봇 '느리'입니다.\n어떤 도움이 필요하신가요? 아래 버튼을 누르시거나 직접 질문을 입력해주세요.",
    },
  ]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const sessionIdRef = useRef<number | null>(null);
  const scrollAnchorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollAnchorRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function updateMessage(
    id: string,
    update: Partial<ChatMessage> | ((m: ChatMessage) => ChatMessage)
  ) {
    setMessages((prev) =>
      prev.map((m) =>
        m.id !== id ? m : typeof update === "function" ? update(m) : { ...m, ...update }
      )
    );
  }

  async function consumeStream(res: Response, botMsgId: string) {
    if (!res.ok || !res.body) throw new Error(`요청 실패 (${res.status})`);

    const reader = res.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let sep;
      while ((sep = buffer.indexOf("\n\n")) !== -1) {
        const block = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);

        let eventType = "message";
        const dataLines: string[] = [];
        for (const line of block.split("\n")) {
          if (line.startsWith("event: ")) eventType = line.slice(7);
          else if (line.startsWith("data: ")) dataLines.push(line.slice(6));
        }
        const data = dataLines.join("\n");
        if (!data && eventType === "message") continue;

        if (eventType === "sources") {
          updateMessage(botMsgId, { sources: JSON.parse(data) as ChatSource[] });
        } else if (eventType === "awaiting_continue") {
          const t = JSON.parse(data) as { message_id: number };
          updateMessage(botMsgId, { awaitingContinueId: t.message_id });
        } else if (eventType === "done") {
          sessionIdRef.current = (JSON.parse(data) as { session_id: number }).session_id;
        } else {
          updateMessage(botMsgId, (m) => ({ ...m, content: m.content + data }));
        }
      }
    }
  }

  async function send(query: string) {
    if (!query.trim() || isStreaming) return;

    const botMsgId = `a-${Date.now()}`;
    setMessages((prev) => [
      ...prev,
      { id: `u-${Date.now()}`, role: "user", content: query },
      { id: botMsgId, role: "assistant", content: "" },
    ]);
    setInput("");
    setIsStreaming(true);

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: query, session_id: sessionIdRef.current }),
      });
      await consumeStream(res, botMsgId);
    } catch {
      updateMessage(botMsgId, {
        content: "죄송합니다, 서버 연결에 문제가 발생했습니다. API 서버가 켜져 있는지 확인해 주세요.",
      });
    } finally {
      setIsStreaming(false);
    }
  }

  async function continueAnswer(sourceMsgId: string, messageId: number) {
    if (isStreaming) return;
    updateMessage(sourceMsgId, { awaitingContinueId: undefined });

    const botMsgId = `a-${Date.now()}`;
    setMessages((prev) => [
      ...prev,
      { id: `u-${Date.now()}`, role: "user", content: "네" },
      { id: botMsgId, role: "assistant", content: "" },
    ]);
    setIsStreaming(true);

    try {
      const res = await fetch(`${API_BASE}/chat/continue`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message_id: messageId }),
      });
      await consumeStream(res, botMsgId);
    } catch {
      updateMessage(botMsgId, {
        content: "죄송합니다, 서버 연결에 문제가 발생했습니다. API 서버가 켜져 있는지 확인해 주세요.",
      });
    } finally {
      setIsStreaming(false);
    }
  }

  const lastMessageId = messages[messages.length - 1]?.id;

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-surface font-body-md antialiased text-on-surface md:items-center">
      {/* Mobile Container */}
      <div className="relative mx-auto flex h-full w-full max-w-[720px] flex-col bg-surface shadow-none md:border md:border-outline-variant md:shadow-lg">
        <TopAppBar />

        {/* Chat Content Scroll Area */}
        <main className="relative flex flex-1 flex-col gap-6 overflow-y-auto scroll-smooth bg-surface-container-lowest px-container-padding pt-20 pb-[160px]">
          {messages.map((msg) =>
            msg.role === "user" ? (
              <div key={msg.id} className="flex w-full flex-col items-end gap-1 self-end pl-12">
                <span className="pr-1 text-label-sm font-label-sm text-on-surface-variant">나</span>
                <div className="w-full max-w-full rounded-2xl rounded-br-sm border border-outline-variant/30 bg-surface-container p-4 text-body-md font-body-md text-on-surface shadow-sm sm:max-w-[85%]">
                  {msg.content}
                </div>
              </div>
            ) : (
              <div key={msg.id} className="flex w-full items-start gap-3 sm:max-w-[90%]">
                <div className="mt-1 flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-full border border-outline-variant bg-surface-variant">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={NEURI_AVATAR}
                    alt="느리"
                    className="h-full w-full object-cover"
                  />
                </div>
                <div className="flex flex-1 flex-col gap-1">
                  <span className="text-label-sm font-label-sm text-on-surface-variant">상속자들</span>
                  <div className="w-full rounded-2xl rounded-tl-sm border border-outline-variant/30 bg-surface-container-high p-4 text-body-md font-body-md text-on-surface shadow-sm">
                    <p
                      className={`whitespace-pre-wrap ${
                        isStreaming && msg.id === lastMessageId ? "streaming-cursor" : ""
                      }`}
                    >
                      {msg.content || (isStreaming ? "생각하는 중..." : "")}
                    </p>
                  </div>

                  {msg.awaitingContinueId !== undefined && (
                    <button
                      type="button"
                      onClick={() => continueAnswer(msg.id, msg.awaitingContinueId!)}
                      disabled={isStreaming}
                      className="mt-2 self-start rounded-full border border-[#f52d81] bg-surface-container-lowest px-4 py-2 text-label-sm font-bold text-[#f52d81] transition-colors hover:bg-surface-variant"
                    >
                      네, 더 설명해 주세요
                    </button>
                  )}

                  {msg.id !== "welcome" && msg.content && (!isStreaming || msg.id !== lastMessageId) && (
                    <p className="mt-1 px-1 text-label-sm font-label-sm text-on-surface-variant opacity-60">
                      {DISCLAIMER}
                    </p>
                  )}

                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-2 w-full rounded-xl border border-outline-variant/30 bg-surface p-4 shadow-sm">
                      <div className="mb-2 flex items-center gap-2">
                        <span className="material-symbols-outlined text-[20px] text-primary">
                          gavel
                        </span>
                        <span className="text-label-sm font-label-sm font-bold text-primary">
                          참고 문서
                        </span>
                      </div>
                      <ul className="space-y-2">
                        {msg.sources.map((s, i) => (
                          <li key={i} className="flex items-start gap-2">
                            <span className="material-symbols-outlined mt-0.5 text-[18px] text-outline">
                              {SOURCE_ICON[s.source_type]}
                            </span>
                            <span className="flex-1 text-body-md font-body-md text-on-surface-variant">
                              {s.url ? (
                                <a
                                  href={s.url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="text-primary underline underline-offset-2"
                                >
                                  {s.title}
                                </a>
                              ) : (
                                s.title
                              )}
                              {s.page ? ` p.${s.page}` : ""} · 유사도 {s.score}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            )
          )}

          {/* Typing Indicator */}
          {isStreaming && messages[messages.length - 1]?.role === "user" && (
            <div className="flex w-full items-start gap-3 sm:max-w-[90%]">
              <div className="mt-1 flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-full border border-outline-variant bg-surface-variant">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={NEURI_AVATAR} alt="느리" className="h-full w-full object-cover" />
              </div>
              <div className="mt-2 flex w-16 items-center justify-center gap-1 rounded-2xl rounded-tl-sm bg-surface-container p-3">
                <div className="h-2 w-2 animate-pulse rounded-full bg-on-surface-variant"></div>
                <div className="h-2 w-2 animate-pulse rounded-full bg-on-surface-variant delay-75"></div>
                <div className="h-2 w-2 animate-pulse rounded-full bg-on-surface-variant delay-150"></div>
              </div>
            </div>
          )}

          {/* Quick Action Pill Buttons */}
          <div className="mt-2 flex flex-wrap items-center justify-end gap-2 self-end pl-12">
            <button
              type="button"
              disabled={isStreaming}
              onClick={() => send("유언대용신탁과 유류분 반환 청구 관련 주요 판례를 알려주세요.")}
              className="min-h-[36px] rounded-full border border-[#f52d81] bg-surface-container-lowest px-4 py-2 text-label-sm font-bold text-[#f52d81] shadow-sm transition-colors hover:bg-surface-variant active:scale-95 disabled:opacity-50"
            >
              판례 조회
            </button>
            <button
              type="button"
              disabled={isStreaming}
              onClick={() => send("유언대용신탁에서 설정할 수 있는 주요 신탁 내용 및 특약을 검색해주세요.")}
              className="min-h-[36px] rounded-full border border-[#f52d81] bg-surface-container-lowest px-4 py-2 text-label-sm font-bold text-[#f52d81] shadow-sm transition-colors hover:bg-surface-variant active:scale-95 disabled:opacity-50"
            >
              신탁 내용 검색
            </button>
            <button
              type="button"
              disabled={isStreaming}
              onClick={() => send("상속 분쟁 예방을 위한 맞춤 상담 신청 절차를 알려주세요.")}
              className="min-h-[36px] rounded-full border border-[#f52d81] bg-surface-container-lowest px-4 py-2 text-label-sm font-bold text-[#f52d81] shadow-sm transition-colors hover:bg-surface-variant active:scale-95 disabled:opacity-50"
            >
              맞춤 상담 신청
            </button>
          </div>

          <div ref={scrollAnchorRef} />
        </main>

        {/* Chat Input Bar */}
        <div className="fixed bottom-[72px] left-0 z-20 w-full border-t border-outline-variant bg-surface p-gutter md:absolute">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              send(input);
            }}
            className="mx-auto flex w-full max-w-[720px] items-center gap-3"
          >
            <button
              type="button"
              className="flex h-[44px] w-[44px] shrink-0 items-center justify-center rounded-full border border-outline text-on-surface-variant transition-colors hover:bg-surface-variant sm:h-[52px] sm:w-[52px]"
            >
              <span className="material-symbols-outlined text-[24px]">add</span>
            </button>
            <div className="relative flex-1">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    send(input);
                  }
                }}
                placeholder="메시지를 입력하세요..."
                disabled={isStreaming}
                rows={1}
                className="min-h-[44px] max-h-[120px] w-full resize-none overflow-y-auto rounded-3xl border-2 border-outline-variant bg-surface-container-lowest px-4 py-3 text-body-md font-body-md text-on-surface placeholder:text-outline shadow-sm transition-colors focus:border-primary-container focus:ring-0 disabled:opacity-60 sm:min-h-[52px]"
              />
            </div>
            <button
              type="submit"
              disabled={isStreaming || !input.trim()}
              className="flex h-[44px] w-[44px] shrink-0 items-center justify-center rounded-full bg-primary-container text-on-primary-container shadow-sm transition-colors hover:bg-primary active:scale-95 disabled:opacity-50 sm:h-[52px] sm:w-[52px]"
            >
              <span className="material-symbols-outlined translate-x-0.5 text-[24px]">send</span>
            </button>
          </form>
        </div>

        <BottomNavBar />
      </div>
    </div>
  );
}
