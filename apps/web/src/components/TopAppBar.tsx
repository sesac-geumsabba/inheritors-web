"use client";

import { useOnboardingTrigger } from "./OnboardingModal";

export default function TopAppBar() {
  const openOnboarding = useOnboardingTrigger();

  return (
    <header className="fixed left-0 top-0 z-50 flex h-16 w-full items-center justify-between gap-2 border-b border-outline-variant bg-surface px-margin-mobile shadow-sm">
      <div className="flex min-w-0 items-center gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-full bg-secondary-container text-on-secondary-container">
          <span className="material-symbols-outlined icon-fill text-[24px]">favorite</span>
        </div>
        <h1 className="truncate text-headline-sm font-headline-sm text-primary">상속자들</h1>
      </div>

      <div className="flex shrink-0 items-center gap-1.5">
        <button
          type="button"
          onClick={openOnboarding}
          aria-label="서비스 안내"
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-surface-container-high text-on-surface-variant transition-colors hover:bg-surface-variant active:scale-95"
        >
          <span className="material-symbols-outlined text-[18px]">help</span>
        </button>
        <button
          type="button"
          aria-label="글자 크기 조절, 현재 150%"
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-surface-container-high text-label-lg font-label-lg text-on-surface-variant transition-colors hover:bg-surface-variant active:scale-95"
        >
          A+
        </button>
      </div>
    </header>
  );
}
