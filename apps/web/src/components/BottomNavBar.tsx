"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

// ponytail: 목업(docs/design/_1)은 "내 정보/챗봇/리포트/뒤로가기" 4탭이지만, "뒤로가기"를
// 하단 고정 탭으로 두는 건 일반적인 내비게이션 의미와 어긋나서 빼고, 기존 "오늘의 배움"
// 자리는 그대로 두고 "복습하기"(미구현 placeholder)만 새로 실제 라우트가 된 "리포트"로 교체.
const TABS = [
  { href: "/prototype/start", label: "오늘의 배움", icon: "school" },
  { href: "/report", label: "리포트", icon: "description" },
  { href: "/chat", label: "챗봇", icon: "chat_bubble" },
  { href: null, label: "내 정보", icon: "person" },
] as const;

export default function BottomNavBar() {
  const pathname = usePathname();

  return (
    <nav className="fixed bottom-0 left-0 z-50 flex h-[72px] w-full items-center justify-around rounded-t-xl border-t border-outline-variant bg-surface px-gutter pb-2 pt-2 shadow-[0_-2px_10px_rgba(0,0,0,0.05)] md:hidden">
      {TABS.map((tab) => {
        const active = tab.href !== null && tab.href === pathname;
        const className = active
          ? "flex h-full w-[72px] flex-col items-center justify-center rounded-xl bg-brand-pink px-4 py-1 text-white transition-transform duration-200 ease-out active:scale-90"
          : "flex h-full flex-col items-center justify-center rounded-xl px-4 py-1 text-on-surface-variant transition-colors hover:bg-surface-container-high";
        const content = (
          <>
            <span className={`material-symbols-outlined mb-1 ${active ? "icon-fill" : ""}`}>{tab.icon}</span>
            <span className={`text-label-sm font-label-sm ${active ? "font-bold" : ""}`}>{tab.label}</span>
          </>
        );

        return tab.href ? (
          <Link key={tab.label} href={tab.href} className={className}>
            {content}
          </Link>
        ) : (
          <button key={tab.label} type="button" className={className}>
            {content}
          </button>
        );
      })}
    </nav>
  );
}
