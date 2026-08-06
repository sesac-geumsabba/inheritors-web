"use client";

import { createContext, useContext, type ReactNode } from "react";

const OnboardingContext = createContext<(() => void) | null>(null);

export function useOnboardingTrigger(): () => void {
  const openOnboarding = useContext(OnboardingContext);
  if (!openOnboarding) {
    throw new Error("useOnboardingTrigger must be used within OnboardingProvider");
  }
  return openOnboarding;
}

export default function OnboardingProvider({ children }: { children: ReactNode }) {
  // 온보딩은 이제 독립 페이지(/)로 분리됨.
  // TopAppBar의 햄버거 버튼 등에서 트리거할 경우 router.push("/")로 이동.
  function goToOnboarding() {
    if (typeof window !== "undefined") {
      window.location.href = "/";
    }
  }

  return (
    <OnboardingContext.Provider value={goToOnboarding}>
      {children}
    </OnboardingContext.Provider>
  );
}
