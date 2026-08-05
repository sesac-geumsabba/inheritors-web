/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  content: ["./src/**/*.{ts,tsx}"],
  // preflight would reset base element styles (headings, buttons) app-wide,
  // which would visibly change the existing plain-CSS chat page at "/".
  corePlugins: { preflight: false },
  theme: {
    extend: {
      // docs/design/DESIGN.md — "Inheritors Senior Digital Care" 디자인 시스템.
      // 토큰이 전역이라 /prototype/* 페이지들도 같이 새 팔레트를 받는다(의도됨) — 프로토타입은
      // Ollama 백엔드 연결만 고정해서 보존하는 것이고, 화면 톤은 같은 디자인 시스템을 공유한다.
      colors: {
        surface: "#fcf9f8",
        "surface-dim": "#dcd9d9",
        "surface-bright": "#fcf9f8",
        "surface-container-lowest": "#ffffff",
        "surface-container-low": "#f6f3f2",
        "surface-container": "#f0eded",
        "surface-container-high": "#eae7e7",
        "surface-container-highest": "#e5e2e1",
        "surface-variant": "#e5e2e1",
        "on-surface": "#1c1b1b",
        "on-surface-variant": "#5a3f46",
        "inverse-surface": "#313030",
        "inverse-on-surface": "#f3f0ef",
        outline: "#8e6f76",
        "outline-variant": "#e2bdc5",
        "surface-tint": "#ba005c",
        primary: "#b6005a",
        "on-primary": "#ffffff",
        "primary-container": "#e01572",
        "on-primary-container": "#fffbff",
        "inverse-primary": "#ffb1c5",
        secondary: "#885200",
        "on-secondary": "#ffffff",
        "secondary-container": "#fe9d00",
        "on-secondary-container": "#663c00",
        tertiary: "#67585f",
        "on-tertiary": "#ffffff",
        "tertiary-container": "#807077",
        "on-tertiary-container": "#fffbff",
        error: "#ba1a1a",
        "on-error": "#ffffff",
        "error-container": "#ffdad6",
        "on-error-container": "#93000a",
        "primary-fixed": "#ffd9e1",
        "primary-fixed-dim": "#ffb1c5",
        "on-primary-fixed": "#3f001b",
        "on-primary-fixed-variant": "#8f0045",
        "secondary-fixed": "#ffdcbb",
        "secondary-fixed-dim": "#ffb869",
        "on-secondary-fixed": "#2c1700",
        "on-secondary-fixed-variant": "#673d00",
        "tertiary-fixed": "#f2dde5",
        "tertiary-fixed-dim": "#d5c1c9",
        "on-tertiary-fixed": "#23181e",
        "on-tertiary-fixed-variant": "#514349",
        background: "#fcf9f8",
        "on-background": "#1c1b1b",
        // 목업(docs/design/_1~_4)이 CTA/칩/경고 강조색으로 토큰이 아니라 이 값을 직접 씀 —
        // primary(#b6005a)보다 밝고 선명해서 시니어 사용자 눈에 더 잘 띄는 액션 강조색으로 분리.
        "brand-pink": "#f52d81",
        "brand-pink-light": "#fde8f0",
      },
      borderRadius: {
        sm: "0.25rem",
        DEFAULT: "0.5rem",
        md: "0.75rem",
        lg: "1rem",
        xl: "1.5rem",
        full: "9999px",
      },
      spacing: {
        "margin-mobile": "20px",
        base: "8px",
        "container-padding": "24px",
        gutter: "16px",
        "touch-target-min": "56px",
        "stack-gap-lg": "32px",
        "stack-gap-md": "20px",
      },
      fontFamily: {
        "headline-lg": ["Be Vietnam Pro"],
        "headline-lg-mobile": ["Be Vietnam Pro"],
        "headline-md": ["Be Vietnam Pro"],
        "body-lg": ["Noto Sans KR"],
        "body-md": ["Noto Sans KR"],
        "label-lg": ["Noto Sans KR"],
        "label-sm": ["Noto Sans KR"],
        // 기존 페이지가 쓰던 이름 — 값은 새 디자인 시스템에 없어서 이전 그대로 유지
        "headline-sm": ["Noto Sans KR"],
      },
      // FN-SUPP-02: 헤더의 글자 크기 버튼(100/125/150%)이 FontScaleProvider를 통해
      // <html>에 --font-scale CSS 변수를 설정하면, 여기서 쓰는 디자인 시스템 폰트 크기가
      // 전부 calc()로 같이 커진다 — 값 자체는 px 고정(디자인 스펙)이라 rem 트릭이 안 통해서
      // 이 방식을 씀. var(...,1) 폴백은 JS 로드 전(SSR)에도 100%로 정상 렌더되게 해준다.
      fontSize: {
        "headline-lg": [
          "calc(32px * var(--font-scale, 1))",
          { lineHeight: "calc(44px * var(--font-scale, 1))", fontWeight: "700" },
        ],
        "headline-lg-mobile": [
          "calc(28px * var(--font-scale, 1))",
          { lineHeight: "calc(38px * var(--font-scale, 1))", fontWeight: "700" },
        ],
        "headline-md": [
          "calc(24px * var(--font-scale, 1))",
          { lineHeight: "calc(34px * var(--font-scale, 1))", fontWeight: "700" },
        ],
        "body-lg": [
          "calc(20px * var(--font-scale, 1))",
          { lineHeight: "calc(30px * var(--font-scale, 1))", fontWeight: "500" },
        ],
        "body-md": [
          "calc(18px * var(--font-scale, 1))",
          { lineHeight: "calc(28px * var(--font-scale, 1))", fontWeight: "400" },
        ],
        "label-lg": [
          "calc(16px * var(--font-scale, 1))",
          { lineHeight: "calc(24px * var(--font-scale, 1))", letterSpacing: "0.02em", fontWeight: "700" },
        ],
        "label-sm": [
          "calc(14px * var(--font-scale, 1))",
          { lineHeight: "calc(20px * var(--font-scale, 1))", fontWeight: "500" },
        ],
        "headline-sm": [
          "calc(24px * var(--font-scale, 1))",
          { lineHeight: "calc(34px * var(--font-scale, 1))", fontWeight: "700" },
        ],
      },
    },
  },
  plugins: [],
};
