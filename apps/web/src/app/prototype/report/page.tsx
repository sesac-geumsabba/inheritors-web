import TopAppBar from "@/components/TopAppBar";

const RISKS = [
  {
    icon: "account_balance",
    accent: "error" as const,
    title: "상속세 납부 재원 부족",
    description: (
      <>
        부동산 비중이 높아 상속 발생 시 막대한 세금을 현금으로 납부하는 데 어려움이 예상됩니다.{" "}
        <strong>생명보험 신탁</strong> 등을 통한 사전 현금 확보가 필요합니다.
      </>
    ),
  },
  {
    icon: "family_restroom",
    accent: "secondary" as const,
    title: "유류분 반환 청구 소송",
    description: (
      <>
        특정 상속인에게 자산이 편중될 경우, 다른 상속인들의 법적 대응(유류분)이 발생할 수 있습니다. 신탁
        계약을 통해 <strong>사전 증여 및 분배 비율</strong>을 명확히 설정해야 합니다.
      </>
    ),
  },
];

const ACCENT_CLASSES = {
  error: { border: "border-l-error", text: "text-error" },
  secondary: { border: "border-l-secondary", text: "text-secondary" },
};

export default function PrototypeReportPage() {
  return (
    <div className="min-h-[max(884px,100dvh)] pb-[120px]">
      <TopAppBar />

      <main className="px-margin-mobile pt-20">
        <div className="mb-8 flex items-start gap-3 rounded-xl bg-surface-container-highest p-4 shadow-sm">
          <span className="material-symbols-outlined icon-fill mt-0.5 shrink-0 text-on-surface-variant">
            info
          </span>
          <p className="text-label-lg font-label-lg text-on-surface-variant">
            본 리포트는 법적 효력이 없는 참고용 정보입니다. 정확한 진단은 전문가 상담을 권장합니다.
          </p>
        </div>

        <section className="mb-10 text-center">
          <h2 className="mb-3 text-headline-md font-headline-md text-on-background">
            맞춤형 자산승계 리포트
          </h2>
          <p className="text-body-md font-body-md text-on-surface-variant">
            입력하신 정보를 바탕으로 분석한
            <br />
            고객님만의 승계 플랜입니다.
          </p>
        </section>

        <section className="mb-10">
          <h3 className="mb-4 text-body-lg font-body-lg text-on-background">선택 자산 및 신탁 유형</h3>
          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col items-center rounded-2xl border border-outline-variant bg-surface-container-lowest p-5 text-center shadow-[0_4px_12px_rgba(0,0,0,0.04)]">
              <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-secondary-fixed text-on-secondary-fixed">
                <span className="material-symbols-outlined icon-fill">apartment</span>
              </div>
              <span className="mb-1 text-label-lg font-label-lg text-on-surface-variant">자산 유형</span>
              <strong className="text-body-lg font-body-lg text-on-background">아파트/부동산</strong>
            </div>

            <div className="flex flex-col items-center rounded-2xl border border-outline-variant bg-surface-container-lowest p-5 text-center shadow-[0_4px_12px_rgba(0,0,0,0.04)]">
              <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-tertiary-fixed text-on-tertiary-fixed">
                <span className="material-symbols-outlined icon-fill">payments</span>
              </div>
              <span className="mb-1 text-label-lg font-label-lg text-on-surface-variant">
                예상 자산 규모
              </span>
              <strong className="text-body-lg font-body-lg text-on-background">50억 ~ 100억</strong>
            </div>

            <div className="col-span-2 flex items-center gap-4 rounded-2xl border border-outline-variant bg-surface-container-lowest p-6 shadow-[0_4px_12px_rgba(0,0,0,0.04)]">
              <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-primary-fixed text-on-primary-fixed">
                <span className="material-symbols-outlined icon-fill text-[28px]">assured_workload</span>
              </div>
              <div>
                <span className="mb-1 block text-label-lg font-label-lg text-on-surface-variant">
                  추천 신탁 솔루션
                </span>
                <strong className="text-headline-sm font-headline-sm text-primary">생전 수익형 신탁</strong>
                <p className="mt-1 text-body-md font-body-md text-on-surface">
                  생전에는 고객님이 수익을 받고, 사후에 지정된 연속수익자에게 안전하게 이전됩니다.
                </p>
              </div>
            </div>
          </div>
        </section>

        <section className="mb-10">
          <h3 className="mb-4 text-body-lg font-body-lg text-on-background">주요 리스크 체크포인트</h3>
          <div className="flex flex-col gap-4">
            {RISKS.map((risk) => {
              const accent = ACCENT_CLASSES[risk.accent];
              return (
                <div
                  key={risk.title}
                  className={`relative overflow-hidden rounded-2xl border border-y-outline-variant border-r-outline-variant bg-surface p-6 shadow-sm border-l-4 ${accent.border}`}
                >
                  <div className="pointer-events-none absolute right-0 top-0 p-4 opacity-10">
                    <span className={`material-symbols-outlined icon-fill text-[80px] ${accent.text}`}>
                      {risk.icon === "account_balance" ? "warning" : "gavel"}
                    </span>
                  </div>
                  <div className="relative z-10 mb-3 flex items-center gap-2">
                    <span className={`material-symbols-outlined icon-fill ${accent.text}`}>{risk.icon}</span>
                    <h4 className="text-body-lg font-body-lg font-bold text-on-background">{risk.title}</h4>
                  </div>
                  <p className="relative z-10 text-body-md font-body-md text-on-surface-variant">
                    {risk.description}
                  </p>
                </div>
              );
            })}
          </div>
        </section>
      </main>

      <div className="fixed bottom-0 left-0 z-50 w-full bg-surface-container-lowest p-margin-mobile shadow-[0_-8px_24px_rgba(0,0,0,0.06)]">
        <button
          type="button"
          className="flex h-[56px] w-full items-center justify-center gap-2 rounded-xl bg-primary text-on-primary shadow-md transition-colors duration-150 hover:bg-primary-container hover:text-on-primary-container active:scale-[0.98]"
        >
          <span className="material-symbols-outlined">event_available</span>
          <span className="text-label-lg font-label-lg">PB 상담 예약하기</span>
        </button>
      </div>
    </div>
  );
}
