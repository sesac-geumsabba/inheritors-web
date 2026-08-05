"use client";

import Image from "next/image";
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
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 px-container-padding"
        >
          <div className="onboarding-card flex max-h-[90vh] w-full max-w-md flex-col overflow-y-auto rounded-2xl bg-surface p-6 shadow-lg">
            {/* docs/design/_4 목업의 마스코트 히어로 — 스크롤 확장 애니메이션(_2)은
                모달 안에서는 과해서 정적인 버전만 가져옴 */}
            <div className="mb-4 flex h-40 w-full items-center justify-center overflow-hidden rounded-2xl border border-outline-variant/20 bg-brand-pink-light p-4">
              <Image src="/mascot/neuri.png" alt="느리" width={112} height={112} className="h-28 w-28 object-contain" />
            </div>
            <div className="mb-6 flex flex-col items-center gap-2 rounded-2xl border border-outline-variant/20 bg-brand-pink-light/50 p-5 text-center">
              <h2 id="onboarding-title" className="text-headline-md font-headline-md text-on-surface">
                안녕하세요!
              </h2>
              <p className="text-body-lg font-body-lg text-on-surface-variant">
                안전하고 편안한 상속 준비,
                <br />
                <span className="font-bold text-brand-pink">상속자들이 도와드릴게요.</span>
              </p>
            </div>

            <p className="mb-3 text-body-md font-body-md leading-relaxed text-on-surface-variant">
              살아계실 땐 안전하게 <b>월세</b>를 받으시고, 사후엔 자녀에게 <b>안전하게 전달</b>되는
              &ldquo;통장 잠금장치&rdquo;라고 생각하시면 됩니다.
            </p>
            <p className="mb-6 text-body-md font-body-md leading-relaxed text-on-surface-variant">
              신탁회사가 자산을 안전하게 관리하다가 미리 정해두신 방식대로 자녀에게 전달해드립니다. 유언장과
              달리 생전에도 수익을 받으실 수 있고, 분쟁 없이 정확하게 전달됩니다.
            </p>
            <div className="flex flex-col gap-3">
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="flex h-touch-target-min items-center justify-center gap-2 rounded-lg bg-brand-pink text-label-lg font-label-lg font-bold text-white shadow-md transition-all active:scale-[0.98]"
              >
                확인
                <span className="material-symbols-outlined">arrow_forward</span>
              </button>
              <button
                type="button"
                onClick={hideForToday}
                className="h-touch-target-min rounded-lg border border-outline-variant text-label-lg font-label-lg font-bold text-on-surface-variant transition-colors hover:bg-surface-variant"
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
