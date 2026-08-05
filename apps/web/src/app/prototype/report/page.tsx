import TopAppBar from "@/components/TopAppBar";
import BottomNavBar from "@/components/BottomNavBar";

export default function PrototypeReportPage() {
  return (
    <div className="relative mx-auto flex h-full min-h-screen w-full max-w-[430px] flex-col overflow-y-auto bg-surface shadow-none md:border md:border-outline-variant md:shadow-lg">
      <TopAppBar />

      <main className="flex-1 px-container-padding pt-20 pb-28">
        {/* Page Header */}
        <section className="mb-6 flex flex-col gap-2">
          <h2 className="text-headline-md font-headline-md text-on-surface">
            자산승계 리포트
          </h2>
          <p className="text-body-md font-body-md text-on-surface-variant break-keep">
            입력하신 정보를 바탕으로 분석된 현재 자산 현황과 예상 법률 리스크입니다.
          </p>
        </section>

        {/* Asset Breakdown Card */}
        <section className="mb-6 flex flex-col gap-4 rounded-2xl border border-outline-variant/30 bg-[#fff6f8] p-5 shadow-sm md:p-6">
          <h3 className="flex items-center gap-2 text-label-lg font-label-lg text-[#f52d81]">
            <span className="material-symbols-outlined shrink-0">account_balance</span>
            현재 자산 현황 요약
          </h3>
          <div className="flex flex-col gap-4">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-outline-variant/20 pb-3">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-surface-container-high text-on-surface-variant">
                  <span className="material-symbols-outlined">apartment</span>
                </div>
                <span className="text-body-lg font-body-lg break-keep">부동산 (아파트)</span>
              </div>
              <span className="text-label-lg font-label-lg whitespace-nowrap">약 12억 원</span>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-outline-variant/20 pb-3">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-surface-container-high text-on-surface-variant">
                  <span className="material-symbols-outlined">payments</span>
                </div>
                <span className="text-body-lg font-body-lg break-keep">현금 및 예금</span>
              </div>
              <span className="text-label-lg font-label-lg whitespace-nowrap">약 3억 원</span>
            </div>

            <div className="flex flex-wrap items-center justify-between pt-2 gap-2">
              <span className="text-body-lg font-body-lg text-on-surface-variant">총 추정 자산</span>
              <span className="text-headline-md font-headline-md text-[#f52d81] whitespace-nowrap">
                약 15억 원
              </span>
            </div>
          </div>
        </section>

        {/* Legal Risk Section */}
        <section className="mb-6 flex flex-col gap-4 rounded-2xl border border-outline-variant/30 bg-[#fff6f8] p-5 shadow-sm md:p-6">
          <h3 className="flex items-center gap-2 text-label-lg font-label-lg text-error">
            <span className="material-symbols-outlined shrink-0">warning</span>
            법률적 위험 요소 (주의)
          </h3>
          <ul className="flex flex-col gap-4">
            <li className="flex flex-col items-start gap-3 rounded-xl border border-outline-variant/30 bg-surface-container-lowest p-4 shadow-sm md:flex-row">
              <span className="material-symbols-outlined shrink-0 text-error">
                priority_high
              </span>
              <div className="flex w-full flex-col gap-1">
                <strong className="text-label-lg font-label-lg">유류분 반환 청구 소송 위험</strong>
                <p className="text-body-md font-body-md text-on-surface-variant break-keep">
                  특정 자녀에게만 부동산을 증여할 경우, 사후에 다른 자녀들이 유류분 반환을 청구할 가능성이 높습니다.
                </p>
              </div>
            </li>
            <li className="flex flex-col items-start gap-3 rounded-xl border border-outline-variant/30 bg-surface-container-lowest p-4 shadow-sm md:flex-row">
              <span className="material-symbols-outlined shrink-0 text-secondary-container">
                account_balance_wallet
              </span>
              <div className="flex w-full flex-col gap-1">
                <strong className="text-label-lg font-label-lg">상속세 납부 재원 부족</strong>
                <p className="text-body-md font-body-md text-on-surface-variant break-keep">
                  부동산 비중이 높아, 현금 자산만으로는 예상 상속세를 납부하기 어려울 수 있습니다. 사전 대비가 필요합니다.
                </p>
              </div>
            </li>
          </ul>
        </section>
      </main>

      <BottomNavBar />
    </div>
  );
}
