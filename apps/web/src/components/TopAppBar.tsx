"use client";

import { useFontScale } from "./FontScaleProvider";
import { useOnboardingTrigger } from "./OnboardingModal";

export default function TopAppBar() {
  const openOnboarding = useOnboardingTrigger();
  const { scale, increase, decrease } = useFontScale();
  const percent = Math.round(scale * 100);

  return (
    <header
      style={{ fontSize: "16px" }}
      className="fixed left-0 top-0 z-50 flex h-touch-target-min w-full items-center justify-between border-b border-outline-variant bg-surface px-container-padding shadow-sm"
    >
      <div className="flex min-w-0 items-center gap-4">
        {/* ponytail: 목업의 메뉴 버튼 자리를 그대로 쓰되, 별도 내비게이션 드로어는 아직
            없어서 기존 온보딩 트리거로 연결해둠 — 실제 메뉴가 필요해지면 교체 */}
        <h1 className="truncate text-[22px] leading-[30px] font-headline-md font-bold text-primary-container">
          상속자들
        </h1>
      </div>

      <div className="flex shrink-0 items-center gap-1.5 pl-4">
        <button
          type="button"
          onClick={increase}
          disabled={percent >= 150}
          aria-label={`글자 크게, 현재 ${percent}%`}
          className="flex h-8 items-center justify-center rounded-full border border-outline-variant/60 bg-surface-container-lowest px-2.5 text-[13px] font-medium text-on-surface transition-all hover:bg-surface-variant active:scale-95 disabled:opacity-40"
        >
          + 글자 크게
        </button>
        <button
          type="button"
          onClick={decrease}
          disabled={percent <= 100}
          aria-label={`글자 작게, 현재 ${percent}%`}
          className="flex h-8 items-center justify-center rounded-full border border-outline-variant/60 bg-surface-container-lowest px-2.5 text-[13px] font-medium text-on-surface transition-all hover:bg-surface-variant active:scale-95 disabled:opacity-40"
        >
          - 글자 작게
        </button>
      </div>
    </header>
  );
}
