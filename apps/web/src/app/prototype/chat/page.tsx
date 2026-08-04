import TopAppBar from "@/components/TopAppBar";
import BottomNavBar from "@/components/BottomNavBar";

const SOURCES = [
  { icon: "description", text: "대법원 2022. 1. 27. 선고 (유류분 산정 기초재산 제외 관련)" },
  { icon: "menu_book", text: "신탁법 제59조 (유언대용신탁)" },
];

const QUICK_ACTIONS = [
  { label: "주요 판례 쉽게 보기", primary: true },
  { label: "실제 방어 성공 사례", primary: false },
  { label: "신탁 특약 종류 알아보기", primary: false },
];

export default function PrototypeChatPage() {
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

          {/* User Message Bubble */}
          <div className="flex justify-end">
            <div className="max-w-[85%] rounded-2xl rounded-tr-sm border border-outline-variant bg-surface p-5 text-on-surface shadow-[0_2px_12px_rgba(0,0,0,0.04)]">
              <p className="text-body-lg font-body-lg text-on-background">
                큰아들 모르게 건물 넘겨주면 소송 걸리나요?
              </p>
            </div>
          </div>

          {/* Neuri (Bot) Response Bubble */}
          <div className="flex items-start gap-3">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-secondary-container text-on-secondary-container shadow-sm">
              <span className="material-symbols-outlined icon-fill text-[24px]">favorite</span>
            </div>
            <div className="flex w-full max-w-[85%] flex-col gap-3">
              <div className="rounded-2xl rounded-tl-sm bg-tertiary-fixed p-5 text-on-tertiary-fixed shadow-[0_2px_12px_rgba(0,0,0,0.06)]">
                <p className="text-body-lg font-body-lg">
                  네, 어르신. 다른 자녀분들이 유류분 반환 청구 소송을 걸 가능성이 매우 높습니다. 하지만{" "}
                  <strong>&apos;유언대용신탁&apos;</strong>이라는 제도를 잘 활용하시면 소송을 방어하고
                  원하시는 대로 재산을 물려주실 수 있는 방법이 있습니다.
                </p>
              </div>

              {/* Source Card (RAG Citation) */}
              <div className="w-full rounded-xl border border-outline-variant bg-surface p-4 shadow-sm">
                <div className="mb-3 flex items-center gap-2">
                  <div className="rounded-full bg-surface-container-high p-1.5 text-secondary">
                    <span className="material-symbols-outlined icon-fill text-[20px]">gavel</span>
                  </div>
                  <span className="text-label-lg font-label-lg text-secondary">관련 판례 및 법령</span>
                </div>
                <ul className="space-y-2">
                  {SOURCES.map((source) => (
                    <li key={source.text} className="flex items-start gap-2">
                      <span className="material-symbols-outlined mt-1 text-[18px] text-outline">
                        {source.icon}
                      </span>
                      <span className="flex-1 text-body-md font-body-md leading-snug text-on-surface-variant">
                        {source.text}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </div>

        {/* Interaction Area (Bottom) - Quick Actions */}
        <div className="z-10 w-full border-t border-surface-container-highest bg-background px-margin-mobile pb-6 pt-4 shadow-[0_-8px_24px_rgba(0,0,0,0.02)]">
          <p className="mb-3 px-1 text-label-lg font-label-lg text-on-surface-variant">추천 질문</p>
          <div className="flex flex-col gap-3">
            {QUICK_ACTIONS.map((action) => (
              <button
                key={action.label}
                type="button"
                className={
                  action.primary
                    ? "flex min-h-[56px] w-full items-center justify-between rounded-xl bg-primary px-6 text-body-lg font-body-lg font-bold text-on-primary shadow-[0_4px_12px_rgba(177,37,0,0.2)] transition-all duration-200 hover:bg-primary-container active:scale-[0.98]"
                    : "flex min-h-[56px] w-full items-center justify-between rounded-xl border border-outline-variant bg-surface px-6 text-body-lg font-body-lg font-bold text-on-surface shadow-sm transition-all duration-200 hover:bg-surface-variant active:scale-[0.98]"
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
        </div>
      </main>

      <BottomNavBar />
    </div>
  );
}
