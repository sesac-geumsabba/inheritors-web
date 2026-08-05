"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

const FONT_SCALE_KEY = "font-scale";
const LEVELS = [1, 1.25, 1.5] as const;
type FontScale = (typeof LEVELS)[number];

function readSavedScale(): FontScale {
  if (typeof window === "undefined") return 1;
  const saved = Number(window.localStorage.getItem(FONT_SCALE_KEY));
  return (LEVELS as readonly number[]).includes(saved) ? (saved as FontScale) : 1;
}

const FontScaleContext = createContext<{ scale: FontScale; cycle: () => void } | null>(null);

export function useFontScale() {
  const ctx = useContext(FontScaleContext);
  if (!ctx) {
    throw new Error("useFontScale must be used within FontScaleProvider");
  }
  return ctx;
}

export default function FontScaleProvider({ children }: { children: ReactNode }) {
  // 실제 CSS 배율(scale)은 localStorage에서 지연 초기화 — 저장된 값이 있으면 마운트되자마자
  // 그 값으로 --font-scale을 건다(추가 리렌더 없이 바로 반영, 화면 크기 깜빡임 없음).
  const [scale, setScale] = useState<FontScale>(readSavedScale);
  // 하지만 컴포넌트가 렌더하는 텍스트(버튼 라벨 "가"/"가+")는 scale을 바로 쓰면 안 된다 —
  // 서버는 항상 100%로 그리는데 재방문자는 클라이언트 첫 렌더부터 저장된 값(예: 150%)으로
  // 그려서 하이드레이션 불일치 에러가 난다(실측 확인). mounted 이전엔 무조건 100%로 노출해
  // 서버 마크업과 일치시키고, 마운트 직후 한 프레임 만에 실제 값으로 갱신한다.
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    document.documentElement.style.setProperty("--font-scale", String(scale));
    window.localStorage.setItem(FONT_SCALE_KEY, String(scale));
  }, [scale]);

  function cycle() {
    const i = LEVELS.indexOf(scale);
    setScale(LEVELS[(i + 1) % LEVELS.length]);
  }

  return (
    <FontScaleContext.Provider value={{ scale: mounted ? scale : 1, cycle }}>
      {children}
    </FontScaleContext.Provider>
  );
}
