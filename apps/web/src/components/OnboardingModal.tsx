"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

const HIDDEN_UNTIL_KEY = "onboarding-hidden-until";
const HIDE_DURATION_MS = 24 * 60 * 60 * 1000;

function isCurrentlyHidden(): boolean {
  const hiddenUntil = Number(localStorage.getItem(HIDDEN_UNTIL_KEY));
  return Boolean(hiddenUntil) && Date.now() < hiddenUntil;
}

const OnboardingContext = createContext<(() => void) | null>(null);

export function useOnboardingTrigger(): () => void {
  const openOnboarding = useContext(OnboardingContext);
  if (!openOnboarding) {
    throw new Error("useOnboardingTrigger must be used within OnboardingProvider");
  }
  return openOnboarding;
}

export default function OnboardingProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!isCurrentlyHidden()) setOpen(true);
  }, []);

  function hideForToday() {
    localStorage.setItem(HIDDEN_UNTIL_KEY, String(Date.now() + HIDE_DURATION_MS));
    setOpen(false);
  }

  return (
    <OnboardingContext.Provider value={() => setOpen(true)}>
      {children}

      {open && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="onboarding-title"
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 px-margin-mobile"
        >
          <div className="onboarding-card w-full max-w-md rounded-xl bg-surface p-6 shadow-lg">
            <h2 id="onboarding-title" className="text-headline-sm font-headline-sm text-on-surface mb-3">
              유언대용신탁이 처음이신가요?
            </h2>
            <p className="text-body-md font-body-md text-on-surface-variant leading-relaxed mb-3">
              살아계실 땐 안전하게 <b>월세</b>를 받으시고, 사후엔 자녀에게 <b>안전하게 전달</b>되는
              &ldquo;통장 잠금장치&rdquo;라고 생각하시면 됩니다.
            </p>
            <p className="text-body-md font-body-md text-on-surface-variant leading-relaxed mb-6">
              신탁회사가 자산을 안전하게 관리하다가 미리 정해두신 방식대로 자녀에게 전달해드립니다. 유언장과
              달리 생전에도 수익을 받으실 수 있고, 분쟁 없이 정확하게 전달됩니다.
            </p>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="flex-1 h-12 rounded-xl bg-primary text-on-primary font-bold text-label-lg font-label-lg active:scale-[0.98] transition-transform"
              >
                확인
              </button>
              <button
                type="button"
                onClick={hideForToday}
                className="flex-1 h-12 rounded-xl border border-outline-variant text-on-surface-variant font-bold text-label-lg font-label-lg hover:bg-surface-variant transition-colors"
              >
                오늘 하루 보지 않기
              </button>
            </div>
          </div>
        </div>
      )}
    </OnboardingContext.Provider>
  );
}
