import FontScaleProvider from "@/components/FontScaleProvider";
import OnboardingProvider from "@/components/OnboardingModal";
import "./globals.css";

export const metadata = {
  title: "상속자들 | 유언대용신탁 자산승계 설계 챗봇",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko" className="light">
      <head>
        <link href="https://fonts.googleapis.com" rel="preconnect" />
        <link crossOrigin="" href="https://fonts.gstatic.com" rel="preconnect" />
        <link
          href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;700&family=Noto+Sans+KR:wght@400;500;700&display=swap"
          rel="stylesheet"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="antialiased">
        {/* 반응형 대신 iPhone 14 Pro Max 폭(430px)에 항상 고정 — 창이 넓어져도 데스크톱
            레이아웃으로 안 바뀌게 한다. [transform:translateZ(0)]는 시각 효과가 아니라
            새 containing block을 만드는 트릭: 안 걸면 TopAppBar/BottomNavBar 같은
            position:fixed 자식들이 이 프레임이 아니라 브라우저 창 전체 폭을 기준으로
            눕는다(이게 바로 넓은 화면에서 하단 내비가 안 보이던 원인). */}
        <div className="flex min-h-screen justify-center bg-on-background/10">
          <div className="relative flex w-full max-w-[430px] flex-col overflow-hidden border-x border-outline-variant/30 bg-surface shadow-2xl [transform:translateZ(0)]">
            <FontScaleProvider>
              <OnboardingProvider>{children}</OnboardingProvider>
            </FontScaleProvider>
          </div>
        </div>
      </body>
    </html>
  );
}
