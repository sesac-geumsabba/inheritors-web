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

interface McpStatus {
  called: boolean;
  tools: string[];
  reason: string;
}

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: ChatSource[];
  mcpStatus?: McpStatus;
  awaitingContinueId?: number;
  // 서버가 "이 답변은 몇 번째 이어보기 결과인지"를 함께 보내준 값 — 다음 이어보기 요청 시
  // continue_count로 그대로 +1 해서 돌려줘야 서버가 상한(MAX_CONTINUE_DEPTH)을 셀 수 있다.
  awaitingContinueCount?: number;
}

const DISCLAIMER =
  "본 내용은 정보 제공을 목적으로 작성되었으며, 정확한 내용 및 적용 여부는 반드시 전문가와 상담하시기 바랍니다.";

const QUICK_ACTIONS = [
  {
    label: "주요 판례 쉽게 보기",
    query: "유언대용신탁과 유류분 반환 청구 관련 대표 판례를 알려주세요.",
    primary: true,
  },
  {
    label: "실제 방어 성공 사례",
    query: "시니어 자산가가 자녀 간 상속 분쟁을 예방하기 위해 신탁을 활용한 실생활 사례를 보여주세요.",
    primary: false,
  },
  {
    label: "신탁 특약 종류 알아보기",
    query: "유언대용신탁에서 설정할 수 있는 주요 특약 종류에는 무엇이 있나요?",
    primary: false,
  },
];

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "안녕하세요. 유언대용신탁에 대해 궁금하신 점을 편하게 물어보세요.",
    },
  ]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const sessionIdRef = useRef<number | null>(null);
  const scrollAnchorRef = useRef<HTMLDivElement>(null);
  // isStreaming state는 다음 렌더까지 반영이 늦어질 수 있어(연타/엔터 연타 시 레이스),
  // 요청 시작 시점에 동기적으로 막을 수 있는 ref 락을 별도로 둔다.
  const isBusyRef = useRef(false);

  useEffect(() => {
    scrollAnchorRef.current?.scrollIntoView({ behavior: "smooth" });
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
        } else if (eventType === "mcp_status") {
          updateMessage(botMsgId, { mcpStatus: JSON.parse(data) as McpStatus });
        } else if (eventType === "awaiting_continue") {
          const t = JSON.parse(data) as { message_id: number; continue_count: number };
          updateMessage(botMsgId, {
            awaitingContinueId: t.message_id,
            awaitingContinueCount: t.continue_count,
          });
        } else if (eventType === "done") {
          sessionIdRef.current = (JSON.parse(data) as { session_id: number }).session_id;
        } else {
          updateMessage(botMsgId, (m) => ({ ...m, content: m.content + data }));
        }
      }
    }
  }

  async function send(query: string) {
    if (!query.trim() || isBusyRef.current) return;
    isBusyRef.current = true;

    const botMsgId = `a-${Date.now()}`;
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
      isBusyRef.current = false;
    }
  }

  async function continueAnswer(sourceMsgId: string, messageId: number, continueCount: number) {
    if (isBusyRef.current) return;
    isBusyRef.current = true;
    // 클릭 즉시 버튼을 없애서 같은 답변에 대해 다시 누를 수 없게 한다.
    updateMessage(sourceMsgId, { awaitingContinueId: undefined, awaitingContinueCount: undefined });

    const botMsgId = `a-${Date.now()}`;
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
        body: JSON.stringify({ message_id: messageId, continue_count: continueCount + 1 }),
      });
      await consumeStream(res, botMsgId);
    } catch {
      updateMessage(botMsgId, {
        content: "죄송합니다, 서버 연결에 문제가 발생했습니다. API 서버가 켜져 있는지 확인해 주세요.",
      });
    } finally {
      setIsStreaming(false);
      isBusyRef.current = false;
    }
  }

  const lastMessageId = messages[messages.length - 1]?.id;

  return (
    <div className="flex min-h-[max(884px,100dvh)] flex-col">
      <TopAppBar />

      <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col overflow-hidden pb-[84px] pt-16 md:my-8 md:rounded-2xl md:border md:border-outline-variant md:pb-0 md:pt-0 md:shadow-lg">
        {/* Viewing Area (Top) - Chat History */}
        <div className="no-scrollbar flex-1 space-y-6 overflow-y-auto bg-background px-margin-mobile py-6">
          <div className="flex justify-center">
            <span className="rounded-full bg-surface-container-high px-4 py-1 text-label-lg font-label-lg text-on-surface-variant opacity-80 shadow-sm">
              법률 상담 시작
            </span>
          </div>

          {messages.map((msg) =>
            msg.role === "user" ? (
              <div key={msg.id} className="flex justify-end">
                <div className="max-w-[85%] rounded-2xl rounded-tr-sm border border-outline-variant bg-surface p-5 text-on-surface shadow-[0_2px_12px_rgba(0,0,0,0.04)]">
                  <p className="text-body-lg font-body-lg text-on-background">{msg.content}</p>
                </div>
              </div>
            ) : (
              <div key={msg.id} className="flex items-start gap-3">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-secondary-container text-on-secondary-container shadow-sm">
                  <span className="material-symbols-outlined icon-fill text-[24px]">favorite</span>
                </div>
                <div className="flex w-full max-w-[85%] flex-col gap-3">
                  <div className="rounded-2xl rounded-tl-sm bg-tertiary-fixed p-5 text-on-tertiary-fixed shadow-[0_2px_12px_rgba(0,0,0,0.06)]">
                    <p
                      className={`whitespace-pre-wrap text-body-lg font-body-lg ${
                        isStreaming && msg.id === lastMessageId ? "streaming-cursor" : ""
                      }`}
                    >
                      {msg.content || (isStreaming ? "생각하는 중..." : "")}
                    </p>
                  </div>

                  {msg.awaitingContinueId !== undefined && (
                    <button
                      type="button"
                      onClick={() =>
                        continueAnswer(msg.id, msg.awaitingContinueId!, msg.awaitingContinueCount ?? 0)
                      }
                      disabled={isStreaming}
                      className="self-start rounded-full border border-outline-variant bg-surface px-4 py-2 text-label-lg font-label-lg text-secondary shadow-sm transition-all active:scale-[0.98] disabled:opacity-50"
                    >
                      네, 더 설명해주세요
                    </button>
                  )}

                  {/* 법률/세무 자문 아님을 고지하는 면책 문구 — 답변 밑에 항상 옅게 노출 */}
                  {msg.id !== "welcome" && msg.content && (!isStreaming || msg.id !== lastMessageId) && (
                    <p className="px-1 text-label-md font-label-md text-on-surface-variant opacity-60">
                      {DISCLAIMER}
                    </p>
                  )}

                  {/* Source Card (RAG Citation) */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="w-full rounded-xl border border-outline-variant bg-surface p-4 shadow-sm">
                      <div className="mb-3 flex items-center gap-2">
                        <div className="rounded-full bg-surface-container-high p-1.5 text-secondary">
                          <span className="material-symbols-outlined icon-fill text-[20px]">gavel</span>
                        </div>
                        <span className="text-label-lg font-label-lg text-secondary">참고 문서</span>
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
                                  className="text-secondary underline underline-offset-2"
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

                  {/* MCP 호출 여부/이유 — 참고 문서 카드 바로 아래에 노출 */}
                  {msg.mcpStatus?.called && (
                    <div className="px-1 text-label-md font-label-md text-on-surface-variant opacity-70">
                      <p>korean-law-mcp를 호출했습니다</p>
                      {msg.mcpStatus.reason && <p>{msg.mcpStatus.reason}</p>}
                    </div>
                  )}
                </div>
              </div>
            )
          )}
          <div ref={scrollAnchorRef} />
        </div>

        {/* Interaction Area (Bottom) */}
        <div className="z-10 w-full border-t border-surface-container-highest bg-background px-margin-mobile pb-6 pt-4 shadow-[0_-8px_24px_rgba(0,0,0,0.02)]">
          {messages.length <= 1 && (
            <>
              <p className="mb-3 px-1 text-label-lg font-label-lg text-on-surface-variant">추천 질문</p>
              <div className="mb-4 flex flex-col gap-3">
                {QUICK_ACTIONS.map((action) => (
                  <button
                    key={action.label}
                    type="button"
                    disabled={isStreaming}
                    onClick={() => send(action.query)}
                    className={
                      action.primary
                        ? "flex min-h-[56px] w-full items-center justify-between rounded-xl bg-primary px-6 text-body-lg font-body-lg font-bold text-on-primary shadow-[0_4px_12px_rgba(177,37,0,0.2)] transition-all duration-200 hover:bg-primary-container active:scale-[0.98] disabled:opacity-50"
                        : "flex min-h-[56px] w-full items-center justify-between rounded-xl border border-outline-variant bg-surface px-6 text-body-lg font-body-lg font-bold text-on-surface shadow-sm transition-all duration-200 hover:bg-surface-variant active:scale-[0.98] disabled:opacity-50"
                    }
                  >
                    <span>{action.label}</span>
                    <span
                      className={`material-symbols-outlined ${action.primary ? "" : "text-on-surface-variant"}`}
                    >
                      arrow_forward_ios
                    </span>
                  </button>
                ))}
              </div>
            </>
          )}

          <form
            onSubmit={(e) => {
              e.preventDefault();
              send(input);
            }}
            className="flex items-center gap-2"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="궁금한 점을 입력하세요"
              disabled={isStreaming}
              className="min-h-[52px] flex-1 rounded-xl border border-outline-variant bg-surface px-4 text-body-lg font-body-lg text-on-surface outline-none focus:border-primary disabled:opacity-60"
            />
            <button
              type="submit"
              disabled={isStreaming || !input.trim()}
              aria-label="전송"
              className="flex h-[52px] w-[52px] shrink-0 items-center justify-center rounded-xl bg-primary text-on-primary shadow-sm transition-all active:scale-95 disabled:opacity-50"
            >
              <span className="material-symbols-outlined">send</span>
            </button>
          </form>
        </div>
      </main>

      <BottomNavBar />
    </div>
  );
}
