"use client";

import { useFontScale } from "./FontScaleProvider";
import { useOnboardingTrigger } from "./OnboardingModal";

export default function TopAppBar() {
  const openOnboarding = useOnboardingTrigger();
  const { scale, increase, decrease } = useFontScale();
  const percent = Math.round(scale * 100);

  return (
    <header className="fixed left-0 top-0 z-50 flex h-touch-target-min w-full items-center justify-between border-b border-outline-variant bg-surface px-container-padding shadow-sm">
      <div className="flex min-w-0 items-center gap-4">
        {/* ponytail: 목업의 메뉴 버튼 자리를 그대로 쓰되, 별도 내비게이션 드로어는 아직
            없어서 기존 온보딩 트리거로 연결해둠 — 실제 메뉴가 필요해지면 교체 */}
        <button
          type="button"
          onClick={openOnboarding}
          aria-label="메뉴"
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-on-surface-variant opacity-80 transition-colors duration-150 hover:scale-95 hover:bg-surface-variant"
        >
          <span className="material-symbols-outlined text-[28px]">menu</span>
        </button>
        <h1 className="truncate text-headline-md font-headline-md font-bold text-primary-container">상속자들</h1>
      </div>

      <div className="flex shrink-0 items-center gap-2">
        <button
          type="button"
          onClick={increase}
          disabled={percent >= 150}
          aria-label={`글자 크게, 현재 ${percent}%`}
          className="flex h-10 items-center justify-center rounded border border-outline-variant bg-surface-container-lowest px-3 text-label-sm font-label-sm text-on-surface transition-colors hover:bg-surface-variant disabled:opacity-40"
        >
          +글자 크게
        </button>
        <button
          type="button"
          onClick={decrease}
          disabled={percent <= 100}
          aria-label={`글자 작게, 현재 ${percent}%`}
          className="flex h-10 items-center justify-center rounded border border-outline-variant bg-surface-container-lowest px-3 text-label-sm font-label-sm text-on-surface transition-colors hover:bg-surface-variant disabled:opacity-40"
        >
          -글자 작게
        </button>
      </div>
    </header>
  );
}
