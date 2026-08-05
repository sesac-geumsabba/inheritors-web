"use client";

import Image from "next/image";
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

const QUICK_ACTIONS = [
  { label: "판례 조회", query: "유언대용신탁과 유류분 반환 청구 관련 대표 판례를 알려주세요." },
  {
    label: "신탁 내용 검색",
    query: "유언대용신탁에서 설정할 수 있는 주요 특약 종류에는 무엇이 있나요?",
  },
  { label: "맞춤 상담 신청", query: "제 상황에 맞는 유언대용신탁 상담을 받고 싶어요." },
];

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "안녕하세요! 상속자들의 법률 도우미 챗봇 '느리'입니다.\n어떤 도움이 필요하신가요? 아래 버튼을 누르시거나 직접 질문을 입력해주세요.",
    },
  ]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const sessionIdRef = useRef<number | null>(null);
  const scrollAnchorRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  // 토큰이 올 때마다 messages가 바뀌어서 매번 무조건 바닥으로 스크롤하면, 답변이 스트리밍되는
  // 동안 위로 스크롤해서 이전 대화를 보려고 해도 계속 아래로 끌려 내려간다 — 사용자가 이미
  // 바닥 근처에 있을 때만("따라가기" 중일 때만) 자동 스크롤하도록 추적한다.
  const isNearBottomRef = useRef(true);

  function handleScroll() {
    const el = scrollContainerRef.current;
    if (!el) return;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    isNearBottomRef.current = distanceFromBottom < 120;
  }

  useEffect(() => {
    if (isNearBottomRef.current) {
      scrollAnchorRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  function updateMessage(id: string, update: Partial<ChatMessage> | ((m: ChatMessage) => ChatMessage)) {
    setMessages((prev) =>
      prev.map((m) => (m.id !== id ? m : typeof update === "function" ? update(m) : { ...m, ...update }))
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
    isNearBottomRef.current = true; // 내가 직접 보낸 메시지는 항상 화면에 따라와야 함
    setMessages((prev) => [
      ...prev,
      { id: `u-${Date.now()}`, role: "user", content: query },
      { id: botMsgId, role: "assistant", content: "" },
    ]);
    setInput("");
    setIsStreaming(true);

    try {
      const res = await fetch(`${API_BASE}/chat/openai`, {
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
    isNearBottomRef.current = true; // "네, 더 설명해주세요" 클릭도 내 액션이니 따라가기 재개
    setMessages((prev) => [
      ...prev,
      { id: `u-${Date.now()}`, role: "user", content: "네" },
      { id: botMsgId, role: "assistant", content: "" },
    ]);
    setIsStreaming(true);

    try {
      const res = await fetch(`${API_BASE}/chat/openai/continue`, {
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
  const showQuickActions = messages.length <= 1;

  return (
    <div className="flex min-h-[max(884px,100dvh)] flex-col bg-surface-container-lowest">
      <TopAppBar />

      <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col overflow-hidden pb-[72px] pt-touch-target-min md:my-8 md:rounded-2xl md:border md:border-outline-variant md:pb-0 md:pt-0 md:shadow-lg">
        {/* Viewing Area (Top) - Chat History */}
        <div
          ref={scrollContainerRef}
          onScroll={handleScroll}
          className="no-scrollbar flex-1 space-y-6 overflow-y-auto bg-surface-container-lowest px-container-padding pt-stack-gap-md pb-6"
        >
          {messages.map((msg) =>
            msg.role === "user" ? (
              <div key={msg.id} className="flex w-full items-end justify-end gap-3 self-end">
                <div className="flex max-w-[85%] flex-col items-end gap-1">
                  <span className="pr-1 text-label-sm font-label-sm text-on-surface-variant">나</span>
                  <div className="rounded-2xl rounded-br-sm border border-outline-variant/30 bg-surface-container p-4 text-on-surface shadow-sm">
                    <p className="whitespace-pre-wrap text-body-md font-body-md">{msg.content}</p>
                  </div>
                </div>
              </div>
            ) : (
              <div key={msg.id} className="flex w-full max-w-[90%] items-start gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-full border border-outline-variant bg-surface-variant">
                  <Image src="/mascot/neuri.png" alt="느리" width={40} height={40} className="h-full w-full object-cover" />
                </div>
                <div className="flex flex-col gap-1">
                  <span className="text-label-sm font-label-sm text-on-surface-variant">상속자들</span>

                  {!msg.content && isStreaming && msg.id === lastMessageId ? (
                    <div className="flex w-16 items-center justify-center gap-1 rounded-2xl rounded-tl-sm bg-surface-container p-3">
                      <div className="h-2 w-2 animate-pulse rounded-full bg-on-surface-variant" />
                      <div className="h-2 w-2 animate-pulse rounded-full bg-on-surface-variant delay-75" />
                      <div className="h-2 w-2 animate-pulse rounded-full bg-on-surface-variant delay-150" />
                    </div>
                  ) : (
                    <div className="rounded-2xl rounded-tl-sm border border-outline-variant/30 bg-surface-container-high p-4 text-on-surface shadow-sm">
                      <p
                        className={`whitespace-pre-wrap text-body-md font-body-md ${
                          isStreaming && msg.id === lastMessageId ? "streaming-cursor" : ""
                        }`}
                      >
                        {msg.content}
                      </p>
                    </div>
                  )}

                  {msg.awaitingContinueId !== undefined && (
                    <button
                      type="button"
                      onClick={() => continueAnswer(msg.id, msg.awaitingContinueId!)}
                      disabled={isStreaming}
                      className="self-start rounded-full border border-brand-pink bg-surface-container-lowest px-4 py-2 text-label-sm font-bold text-brand-pink shadow-sm transition-colors hover:bg-surface-variant disabled:opacity-50"
                    >
                      네, 더 설명해주세요
                    </button>
                  )}

                  {/* 법률/세무 자문 아님을 고지하는 면책 문구 — 답변 밑에 항상 옅게 노출 */}
                  {msg.id !== "welcome" && msg.content && (!isStreaming || msg.id !== lastMessageId) && (
                    <p className="max-w-[280px] px-1 text-label-sm font-label-sm text-on-surface-variant opacity-70">
                      {DISCLAIMER}
                    </p>
                  )}

                  {/* Source Card (RAG Citation) */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="w-full rounded-xl border border-outline-variant/30 bg-surface-container-lowest p-4 shadow-sm">
                      <div className="mb-3 flex items-center gap-2">
                        <div className="rounded-full bg-surface-container-high p-1.5 text-brand-pink">
                          <span className="material-symbols-outlined icon-fill text-[20px]">gavel</span>
                        </div>
                        <span className="text-label-sm font-bold text-brand-pink">참고 문서</span>
                      </div>
                      <ul className="space-y-2">
                        {msg.sources.map((s, i) => (
                          <li key={i} className="flex items-start gap-2">
                            <span className="material-symbols-outlined mt-1 text-[18px] text-outline">
                              {SOURCE_ICON[s.source_type]}
                            </span>
                            <span className="flex-1 text-body-md font-body-md leading-snug text-on-surface-variant">
                              {s.url ? (
                                <a
                                  href={s.url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="text-brand-pink underline underline-offset-2"
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

                  {msg.id === "welcome" && showQuickActions && (
                    <div className="flex w-full flex-wrap justify-end gap-2 pt-1">
                      {QUICK_ACTIONS.map((action) => (
                        <button
                          key={action.label}
                          type="button"
                          disabled={isStreaming}
                          onClick={() => send(action.query)}
                          className="whitespace-nowrap rounded-full border border-brand-pink bg-surface-container-lowest px-4 py-1 text-label-sm font-bold text-brand-pink transition-colors hover:bg-surface-variant disabled:opacity-50"
                        >
                          {action.label}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )
          )}
          <div ref={scrollAnchorRef} />
        </div>

        {/* Interaction Area (Bottom) */}
        <div className="z-10 w-full border-t border-outline-variant bg-surface p-gutter">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              send(input);
            }}
            className="mx-auto flex w-full max-w-2xl items-center gap-3"
          >
            <div className="relative flex-1">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="메시지를 입력하세요..."
                disabled={isStreaming}
                className="h-[52px] w-full rounded-full border-2 border-outline-variant bg-surface-container-lowest px-4 text-on-surface shadow-sm outline-none placeholder:text-outline focus:border-primary-container disabled:opacity-60 text-body-md font-body-md"
              />
            </div>
            <button
              type="submit"
              disabled={isStreaming || !input.trim()}
              aria-label="전송"
              className="flex h-[52px] w-[52px] shrink-0 items-center justify-center rounded-full bg-primary-container text-on-primary-container shadow-sm transition-all active:scale-95 disabled:opacity-50"
            >
              <span className="material-symbols-outlined translate-x-0.5">send</span>
            </button>
          </form>
        </div>
      </main>

      <BottomNavBar />
    </div>
  );
}
