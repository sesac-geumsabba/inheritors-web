"use client";

import { useFontScale } from "./FontScaleProvider";
import { useOnboardingTrigger } from "./OnboardingModal";

export default function TopAppBar() {
  const openOnboarding = useOnboardingTrigger();
  const { cycle } = useFontScale();

  return (
    <header className="sticky top-0 z-10 flex h-touch-target-min w-full items-center justify-between border-b border-outline-variant bg-surface px-container-padding shrink-0">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={openOnboarding}
          aria-label="메뉴"
          className="flex h-10 w-10 items-center justify-center rounded-full text-on-surface-variant opacity-80 transition-colors hover:bg-surface-variant active:scale-95"
        >
          <span className="material-symbols-outlined text-[28px]">menu</span>
        </button>
        <h1 className="font-headline-md text-headline-md font-bold text-primary-container">
          상속자들
        </h1>
      </div>

      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={cycle}
          className="flex min-h-10 items-center justify-center rounded border border-outline-variant px-3 py-1 text-label-sm font-label-sm text-on-surface whitespace-nowrap transition-colors hover:bg-surface-variant active:scale-95"
        >
          +글자 크게
        </button>
        <button
          type="button"
          onClick={cycle}
          className="flex min-h-10 items-center justify-center rounded border border-outline-variant px-3 py-1 text-label-sm font-label-sm text-on-surface whitespace-nowrap transition-colors hover:bg-surface-variant active:scale-95"
        >
          -글자 작게
        </button>
      </div>
    </header>
  );
}
