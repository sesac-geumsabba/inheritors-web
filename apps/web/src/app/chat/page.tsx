"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import TopAppBar from "@/components/TopAppBar";
import BottomNavBar from "@/components/BottomNavBar";
import { CHAT_MESSAGES_STORAGE_KEY, CHAT_SESSION_ID_STORAGE_KEY } from "@/lib/chatStorage";

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
  { label: "판례 조회", query: "유언대용신탁과 유류분 반환 청구 관련 대표 판례를 알려주세요." },
  {
    label: "신탁 내용 검색",
    query: "유언대용신탁에서 설정할 수 있는 주요 특약 종류에는 무엇이 있나요?",
  },
  { label: "맞춤 상담 신청", query: "제 상황에 맞는 유언대용신탁 상담을 받고 싶어요." },
];

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

// apps/api/app/report.py의 MIN_USER_TURNS_FOR_REPORT와 값을 맞춰야 한다 — 여기서 배너를
// 먼저 보여주고 실제 호출은 이 기준 미달로 400이 나면(레이스 발생 시) 안내 메시지로 대체된다.
const REPORT_TURN_THRESHOLD = 6;

// 리포트 등 다른 탭으로 이동했다가 챗봇으로 돌아오면 컴포넌트가 새로 마운트되면서 useState
// 초기값(welcome 메시지 1개)으로 리셋된다 — sessionStorage에 대화/세션ID를 저장해뒀다가
// 마운트 시 복원한다. localStorage가 아니라 sessionStorage인 이유: 탭을 닫으면 자연스럽게
// 새 상담으로 시작해야 하고(브라우저 재시작 후까지 이어질 필요는 없음), 다른 탭/사용자와도
// 안 섞인다.

// 답변 대기/생성 중임을 보여주는 점 3개 — 아직 토큰이 하나도 안 왔을 때(대기 중)는 크게,
// 텍스트가 스트리밍되는 동안엔 문장 끝에 작게 붙여서 "아직 이어서 쓰는 중"임을 표시한다.
function TypingDots({ size = "md" }: { size?: "sm" | "md" }) {
  // span + inline-block: 이 컴포넌트가 <p> 안(스트리밍 중 텍스트 끝)에도 들어가는데, <p>는
  // div 같은 block 요소를 못 담는다(HTML 스펙 — 브라우저가 <p>를 강제로 닫아버려서
  // hydration mismatch 발생, 실측 확인). span은 phrasing content라 <p> 안에서도 안전.
  const dot = size === "sm" ? "h-1.5 w-1.5" : "h-2 w-2";
  return (
    <>
      <span className={`inline-block ${dot} animate-pulse rounded-full bg-on-surface-variant`} />
      <span className={`inline-block ${dot} animate-pulse rounded-full bg-on-surface-variant delay-75`} />
      <span className={`inline-block ${dot} animate-pulse rounded-full bg-on-surface-variant delay-150`} />
    </>
  );
}

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "안녕하세요! 상속자들의 법률 도우미 챗봇 '상속자들'입니다.\n어떤 도움이 필요하신가요? 아래 버튼을 누르시거나 직접 질문을 입력해주세요.",
    },
  ]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const sessionIdRef = useRef<number | null>(null);
  const scrollAnchorRef = useRef<HTMLDivElement>(null);
  // isStreaming state는 다음 렌더까지 반영이 늦어질 수 있어(연타/엔터 연타 시 레이스),
  // 요청 시작 시점에 동기적으로 막을 수 있는 ref 락을 별도로 둔다.
  const isBusyRef = useRef(false);
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

  // 마운트 직후 첫 저장-effect 실행을 건너뛰기 위한 플래그. 복원 effect와 저장 effect가
  // 같은 커밋에서 순서대로 도는데, 저장 effect가 먼저(복원이 적용되기 전) 한 번 돌면서
  // 아직 welcome 메시지뿐인 상태를 그대로 sessionStorage에 덮어써버려 복원 자체가
  // 무의미해지는 레이스가 실측 확인됨 — 그 첫 실행만 건너뛴다.
  const skipNextPersistRef = useRef(true);

  // 마운트 시 저장된 대화 복원 — useState 초기값에서 바로 읽지 않는 이유: Next.js는 이
  // 컴포넌트를 서버에서도 한 번 렌더링하는데(SSR), 그때는 sessionStorage가 없어서 서버가
  // 그린 HTML과 클라이언트 첫 렌더가 달라져 hydration mismatch가 난다. useEffect는 클라이언트
  // 마운트 후에만 도니까 안전하게 한 박자 늦게 복원한다.
  useEffect(() => {
    const savedMessages = sessionStorage.getItem(CHAT_MESSAGES_STORAGE_KEY);
    const savedSessionId = sessionStorage.getItem(CHAT_SESSION_ID_STORAGE_KEY);
    if (savedMessages) {
      try {
        setMessages(JSON.parse(savedMessages) as ChatMessage[]);
      } catch {
        // 저장된 값이 깨져있으면 그냥 welcome 메시지로 시작 — 복구 불가라 무시.
      }
    }
    if (savedSessionId) sessionIdRef.current = Number(savedSessionId);
  }, []);

  // 대화가 바뀔 때마다(스트리밍 도중 포함) 저장 — 리포트 등 다른 탭으로 이동했다가
  // 돌아와도 이어서 볼 수 있어야 한다.
  useEffect(() => {
    if (skipNextPersistRef.current) {
      skipNextPersistRef.current = false;
      return;
    }
    sessionStorage.setItem(CHAT_MESSAGES_STORAGE_KEY, JSON.stringify(messages));
  }, [messages]);

  useEffect(() => {
    if (isNearBottomRef.current) {
      // block: "end" — 앵커가 이제 참고 문서 앞(답변 말풍선 바로 뒤)에 있어서 기본값
      // block: "start"를 쓰면 앵커 자체를 위로 붙이려다 답변이 화면 밖으로 밀려난다.
      scrollAnchorRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
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
        } else if (eventType === "mcp_status") {
          updateMessage(botMsgId, { mcpStatus: JSON.parse(data) as McpStatus });
        } else if (eventType === "awaiting_continue") {
          const t = JSON.parse(data) as { message_id: number; continue_count: number };
          updateMessage(botMsgId, {
            awaitingContinueId: t.message_id,
            awaitingContinueCount: t.continue_count,
          });
        } else if (eventType === "done") {
          const sessionId = (JSON.parse(data) as { session_id: number }).session_id;
          sessionIdRef.current = sessionId;
          sessionStorage.setItem(CHAT_SESSION_ID_STORAGE_KEY, String(sessionId));
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
      isBusyRef.current = false;
    }
  }

  async function continueAnswer(sourceMsgId: string, messageId: number, continueCount: number) {
    if (isBusyRef.current) return;
    isBusyRef.current = true;
    // 클릭 즉시 버튼을 없애서 같은 답변에 대해 다시 누를 수 없게 한다.
    updateMessage(sourceMsgId, { awaitingContinueId: undefined, awaitingContinueCount: undefined });

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
  const showQuickActions = messages.length <= 1;
  const userTurnCount = messages.filter((m) => m.role === "user").length;
  const showReportBanner = userTurnCount >= REPORT_TURN_THRESHOLD && sessionIdRef.current != null;

  return (
    <div className="flex h-[100dvh] flex-col overflow-hidden bg-surface-container-lowest">
      <TopAppBar />

      <main className="flex w-full flex-1 flex-col overflow-hidden bg-surface-container-lowest pt-touch-target-min pb-[148px]">
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
                      <TypingDots />
                    </div>
                  ) : (
                    <div className="rounded-2xl rounded-tl-sm border border-outline-variant/30 bg-surface-container-high p-4 text-on-surface shadow-sm">
                      <p className="whitespace-pre-wrap text-body-md font-body-md">
                        {msg.content}
                        {isStreaming && msg.id === lastMessageId && (
                          <span className="ml-1.5 inline-flex translate-y-[2px] items-center gap-1">
                            <TypingDots size="sm" />
                          </span>
                        )}
                      </p>
                    </div>
                  )}

                  {/* 자동 스크롤 목표점 — 답변 말풍선 바로 뒤에 둔다. 메시지 끝(참고 문서/면책
                      문구 지난 자리)에 두면 sources가 스트리밍 시작 전에 먼저 도착해서 답변을
                      다 안 읽었는데 참고 문서까지 보이게 끌려 내려간다(실측). */}
                  {msg.id === lastMessageId && <div ref={scrollAnchorRef} />}

                  {msg.awaitingContinueId !== undefined && (
                    <button
                      type="button"
                      onClick={() =>
                        continueAnswer(msg.id, msg.awaitingContinueId!, msg.awaitingContinueCount ?? 0)
                      }
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

                  {/* Source Card (RAG Citation) — 기본은 접힌 상태, 눌러야 목록이 펼쳐짐.
                      <details>/<summary>는 네이티브 토글이라 메시지마다 별도 열림 상태를
                      React에서 관리할 필요가 없다. */}
                  {msg.sources && msg.sources.length > 0 && (
                    <details className="group w-full rounded-xl border border-outline-variant/30 bg-surface-container-lowest p-4 shadow-sm">
                      <summary className="flex cursor-pointer list-none items-center gap-2 [&::-webkit-details-marker]:hidden">
                        <div className="rounded-full bg-surface-container-high p-1.5 text-brand-pink">
                          <span className="material-symbols-outlined icon-fill text-[20px]">gavel</span>
                        </div>
                        <span className="flex-1 text-label-sm font-bold text-brand-pink">
                          참고 문서 ({msg.sources.length})
                        </span>
                        <span className="material-symbols-outlined text-outline transition-transform duration-200 group-open:rotate-180">
                          expand_more
                        </span>
                      </summary>
                      <ul className="mt-3 space-y-2">
                        {msg.sources.map((s, i) => (
                          <li key={i} className="flex items-start gap-2">
                            <span className="material-symbols-outlined mt-1 text-[18px] text-outline">
                              {SOURCE_ICON[s.source_type]}
                            </span>
                            <span className="flex-1 text-body-md font-body-md leading-snug text-on-surface-variant">
                              {s.url ? (
                                <a
                                  target="_blank"
                                  rel="noreferrer"
                                  className="text-brand-pink underline underline-offset-2"
                                >
                                  {s.title}
                                </a>
                              ) : (
                                s.title
                              )}
                              <span className="block">유사도 {s.score}</span>
                            </span>
                          </li>
                        ))}
                      </ul>
                    </details>
                  )}

                  {/* MCP 호출 여부/이유 — 참고 문서 카드 바로 아래에 노출 */}
                  {msg.mcpStatus?.called && (
                    <div className="px-1 text-label-md font-label-md text-on-surface-variant opacity-70">
                      <p>korean-law-mcp를 호출했습니다</p>
                      {msg.mcpStatus.reason && <p>{msg.mcpStatus.reason}</p>}
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
          {showReportBanner && (
            <div className="flex w-full max-w-[90%] flex-col gap-2 rounded-2xl border border-brand-pink/30 bg-brand-pink-light p-4 shadow-sm">
              <p className="text-body-md font-body-md text-on-surface">
                지금까지 상담하신 내용을 바탕으로 자산 현황과 리포트를 정리해드릴까요?
              </p>
              <Link
                href={`/report?session_id=${sessionIdRef.current}`}
                className="self-start rounded-full bg-brand-pink px-4 py-2 text-label-sm font-bold text-white transition-colors hover:opacity-90"
              >
                상담 리포트 보기
              </Link>
            </div>
          )}
        </div>

        {/* Interaction Area (Bottom) - Fixed above BottomNavBar on mobile */}
        <div
          style={{ fontSize: "16px" }}
          className="fixed bottom-[72px] left-0 z-40 w-full border-t border-outline-variant bg-surface-container-lowest p-gutter"
        >
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
                className="h-[52px] w-full rounded-full border-2 border-outline-variant bg-surface-container-lowest px-4 text-on-surface shadow-sm outline-none placeholder:text-outline focus:border-primary-container disabled:opacity-60 text-[18px] leading-[28px] font-body-md"
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
