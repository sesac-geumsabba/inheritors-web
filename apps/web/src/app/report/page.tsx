import TopAppBar from "@/components/TopAppBar";
import BottomNavBar from "@/components/BottomNavBar";

// ponytail: FN-CORE-01(자산승계 시뮬레이션) 백엔드가 아직 없어서 docs/design/_1 목업의
// 예시 수치를 그대로 씀 — 시뮬레이션 기능이 생기면 실제 입력값으로 교체.
const ASSETS = [
  { icon: "apartment", label: "부동산 (아파트)", amount: "약 12억 원" },
  { icon: "payments", label: "현금 및 예금", amount: "약 3억 원" },
];

const RISKS = [
  {
    icon: "priority_high",
    title: "유류분 반환 청구 소송 위험",
    description: "특정 자녀에게만 부동산을 증여할 경우, 사후에 다른 자녀들이 유류분 반환을 청구할 가능성이 높습니다.",
  },
  {
    icon: "account_balance_wallet",
    title: "상속세 납부 재원 부족",
    description: "부동산 비중이 높아, 현금 자산만으로는 예상 상속세를 납부하기 어려울 수 있습니다. 사전 대비가 필요합니다.",
  },
];

export default function ReportPage() {
  return (
    <div className="min-h-[max(884px,100dvh)] bg-surface-container-lowest pb-[140px]">
      <TopAppBar />

      <main className="mx-auto flex w-full max-w-2xl flex-col gap-6 px-container-padding pt-[calc(56px+20px)] md:my-8 md:rounded-2xl md:border md:border-outline-variant md:bg-surface md:shadow-lg md:pb-8">
        <section>
          <h2 className="mb-2 text-headline-lg-mobile font-headline-lg-mobile text-on-surface">
            자산승계 리포트
          </h2>
          <p className="text-body-md font-body-md text-on-surface-variant">
            입력하신 정보를 바탕으로 분석된
            <br />
            현재 자산 현황과 예상 법률 리스크입니다.
          </p>
        </section>

        <section className="rounded-2xl border border-outline-variant/30 bg-brand-pink-light p-6 shadow-sm">
          <h3 className="mb-6 flex items-center gap-2 text-label-lg font-label-lg text-brand-pink">
            <span className="material-symbols-outlined">account_balance</span>
            현재 자산 현황 요약
          </h3>
          <div className="flex flex-col gap-4">
            {ASSETS.map((asset) => (
              <div key={asset.label} className="flex items-center justify-between border-b border-outline-variant/20 pb-3">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-surface-container-high text-on-surface-variant">
                    <span className="material-symbols-outlined">{asset.icon}</span>
                  </div>
                  <span className="text-body-lg font-body-lg">{asset.label}</span>
                </div>
                <span className="text-label-lg font-label-lg">{asset.amount}</span>
              </div>
            ))}
            <div className="flex items-center justify-between pt-2">
              <span className="text-body-lg font-body-lg text-on-surface-variant">총 추정 자산</span>
              <span className="text-headline-md font-headline-md text-brand-pink">약 15억 원</span>
            </div>
          </div>
        </section>

        <section className="rounded-2xl border border-outline-variant/30 bg-brand-pink-light p-6 shadow-sm">
          <h3 className="mb-4 flex items-center gap-2 text-label-lg font-label-lg text-error">
            <span className="material-symbols-outlined">warning</span>
            법률적 위험 요소 (주의)
          </h3>
          <ul className="flex flex-col gap-4">
            {RISKS.map((risk) => (
              <li
                key={risk.title}
                className="flex items-start gap-3 rounded-xl border border-outline-variant/30 bg-surface-container-lowest p-4 shadow-sm"
              >
                <span className="material-symbols-outlined icon-fill mt-0.5 text-error">{risk.icon}</span>
                <div>
                  <strong className="mb-1 block text-label-lg font-label-lg">{risk.title}</strong>
                  <p className="text-body-md font-body-md text-on-surface-variant">{risk.description}</p>
                </div>
              </li>
            ))}
          </ul>
        </section>

        <section>
          <button
            type="button"
            className="flex min-h-touch-target-min w-full items-center justify-center gap-2 rounded-full bg-brand-pink py-4 text-label-lg font-label-lg text-white shadow-sm transition-all hover:opacity-90 active:scale-95"
          >
            전문가(PB) 상담 연결하기
            <span className="material-symbols-outlined">arrow_forward</span>
          </button>
        </section>
      </main>

      <BottomNavBar />
    </div>
  );
}
