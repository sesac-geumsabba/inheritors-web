import OnboardingModal from "@/components/OnboardingModal";

export const metadata = {
  title: "유언대용신탁 자산승계 설계 챗봇",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>
        <header>
          <OnboardingModal />
        </header>
        {children}
      </body>
    </html>
  );
}
