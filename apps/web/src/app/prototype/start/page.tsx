import Link from "next/link";
import TopAppBar from "@/components/TopAppBar";
import BottomNavBar from "@/components/BottomNavBar";

export default function PrototypeStartPage() {
  return (
    <div className="flex min-h-[max(884px,100dvh)] flex-col">
      <TopAppBar />

      <main className="flex flex-1 flex-col overflow-y-auto pb-[84px] pt-16 md:pb-0">
        {/* Viewing Area (Top) - Neuri Greeting */}
        <div className="relative flex min-h-[353px] flex-1 flex-col items-center justify-center overflow-hidden bg-gradient-to-b from-surface-container-low to-surface px-margin-mobile py-8">
          <div className="absolute left-1/2 top-1/2 -z-10 aspect-square w-[150%] -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary-fixed opacity-20 blur-3xl" />

          {/* ponytail: 마스코트 이미지 자산 미확정, 자리표시자 사용 */}
          <div className="mb-6 flex h-48 w-48 items-center justify-center rounded-full bg-secondary-container text-on-secondary-container">
            <span className="material-symbols-outlined icon-fill text-[96px]">favorite</span>
          </div>

          <div className="relative z-10 w-full max-w-md rounded-[24px] border border-outline-variant bg-surface p-6 text-center shadow-[0_8px_24px_rgba(177,37,0,0.08)]">
            <p className="mb-2 text-headline-md font-headline-md text-on-surface">안녕하세요!</p>
            <p className="text-body-lg font-body-lg text-on-surface-variant">
              안전하고 편안한 상속 준비,
              <br />
              <span className="font-bold text-primary">네우리</span>가 도와드릴게요.
            </p>
          </div>
        </div>

        {/* Interaction Area (Bottom) - Value Proposition & Actions */}
        <div className="relative flex flex-1 flex-col border-t border-outline-variant bg-surface-container-lowest px-margin-mobile py-8 md:border-none">
          <div className="mx-auto flex h-full w-full max-w-md flex-col justify-between gap-6">
            <div className="flex flex-col gap-4">
              <div className="flex items-start gap-4 rounded-xl border border-outline-variant bg-surface-container p-5 shadow-sm">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-primary-container text-on-primary-container">
                  <span className="material-symbols-outlined icon-fill text-[28px]">lock_person</span>
                </div>
                <div>
                  <h3 className="mb-1 text-body-lg font-body-lg font-bold text-on-surface">통장 잠금장치</h3>
                  <p className="text-body-md font-body-md leading-relaxed text-on-surface-variant">
                    살아계실 땐 안전하게 <b>월세</b>를 받으시고,
                    <br />
                    사후엔 자녀에게 <b>안전하게 전달</b>됩니다.
                  </p>
                </div>
              </div>
            </div>

            <div className="mt-auto pb-4 pt-6">
              <Link
                href="/chat"
                className="flex min-h-[56px] w-full items-center justify-center gap-2 rounded-xl bg-[#f85029] text-headline-sm font-headline-sm text-white shadow-md transition-transform hover:bg-primary active:scale-[0.98]"
              >
                <span>시작하기</span>
                <span className="material-symbols-outlined">arrow_forward</span>
              </Link>
              <p className="mt-4 text-center text-body-md font-body-md text-on-surface-variant opacity-80">
                1분이면 충분해요
              </p>
            </div>
          </div>
        </div>
      </main>

      <BottomNavBar />
    </div>
  );
}
