/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  content: ["./src/**/*.{ts,tsx}"],
  // preflight would reset base element styles (headings, buttons) app-wide,
  // which would visibly change the existing plain-CSS chat page at "/".
  corePlugins: { preflight: false },
  theme: {
    extend: {
      colors: {
        "on-primary-fixed": "#3d0600",
        "on-tertiary-fixed": "#001e2d",
        "on-background": "#271814",
        background: "#fff8f6",
        "surface-variant": "#fadcd5",
        "secondary-fixed-dim": "#ffb4a3",
        "on-tertiary-fixed-variant": "#004c6a",
        "primary-fixed": "#ffdad2",
        "surface-container": "#ffe9e4",
        "surface-tint": "#b52600",
        "surface-dim": "#f1d4cd",
        "on-error-container": "#93000a",
        "tertiary-fixed-dim": "#7fd0ff",
        "inverse-primary": "#ffb4a3",
        "on-secondary-fixed": "#3d0600",
        "inverse-on-surface": "#ffede9",
        "secondary-container": "#f9856a",
        "surface-container-high": "#ffe2db",
        "on-secondary-fixed-variant": "#7f2a16",
        surface: "#fff8f6",
        "error-container": "#ffdad6",
        "outline-variant": "#e4beb5",
        "secondary-fixed": "#ffdad2",
        "on-primary": "#ffffff",
        "primary-fixed-dim": "#ffb4a3",
        "surface-container-highest": "#fadcd5",
        "on-secondary-container": "#701e0b",
        "on-error": "#ffffff",
        secondary: "#9f402a",
        "on-primary-fixed-variant": "#8b1b00",
        "on-tertiary": "#ffffff",
        "on-surface": "#271814",
        outline: "#907068",
        "surface-container-lowest": "#ffffff",
        "tertiary-fixed": "#c5e7ff",
        "on-secondary": "#ffffff",
        "on-tertiary-container": "#fcfcff",
        "tertiary-container": "#007dab",
        "inverse-surface": "#3e2c28",
        "surface-container-low": "#fff0ed",
        "surface-bright": "#fff8f6",
        tertiary: "#006388",
        primary: "#b12500",
        error: "#ba1a1a",
        "on-primary-container": "#fffbff",
        "on-surface-variant": "#5b403a",
        "primary-container": "#d83913",
      },
      borderRadius: {
        DEFAULT: "0.25rem",
        lg: "0.5rem",
        xl: "0.75rem",
        full: "9999px",
      },
      spacing: {
        "margin-mobile": "20px",
      },
      fontFamily: {
        "body-lg": ["Noto Sans KR"],
        "headline-md": ["Noto Sans KR"],
        "body-md": ["Noto Sans KR"],
        "headline-sm": ["Noto Sans KR"],
        "label-lg": ["Noto Sans KR"],
      },
      // FN-SUPP-02: 헤더의 글자 크기 버튼(100/125/150%)이 FontScaleProvider를 통해
      // <html>에 --font-scale CSS 변수를 설정하면, 여기서 쓰는 디자인 시스템 폰트 크기가
      // 전부 calc()로 같이 커진다 — 값 자체는 px 고정(디자인 스펙)이라 rem 트릭이 안 통해서
      // 이 방식을 씀. var(...,1) 폴백은 JS 로드 전(SSR)에도 100%로 정상 렌더되게 해줌.
      fontSize: {
        "body-lg": [
          "calc(20px * var(--font-scale, 1))",
          { lineHeight: "calc(32px * var(--font-scale, 1))", fontWeight: "500" },
        ],
        "headline-md": [
          "calc(28px * var(--font-scale, 1))",
          { lineHeight: "calc(40px * var(--font-scale, 1))", fontWeight: "700" },
        ],
        "body-md": [
          "calc(18px * var(--font-scale, 1))",
          { lineHeight: "calc(28px * var(--font-scale, 1))", fontWeight: "400" },
        ],
        "label-lg": [
          "calc(16px * var(--font-scale, 1))",
          { lineHeight: "calc(24px * var(--font-scale, 1))", letterSpacing: "0.5px", fontWeight: "700" },
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
