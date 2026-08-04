"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { href: "/prototype/start", label: "오늘의 배움", icon: "school" },
  { href: null, label: "복습하기", icon: "history_edu" },
  { href: "/chat", label: "상담소", icon: "chat_bubble" },
  { href: null, label: "내 정보", icon: "person" },
] as const;

export default function BottomNavBar() {
  const pathname = usePathname();

  return (
    <nav className="fixed bottom-0 left-0 z-50 flex h-[84px] w-full items-center justify-around rounded-t-xl bg-surface-container px-4 pb-4 pt-2 shadow-[0_-4px_12px_rgba(0,0,0,0.08)] md:hidden">
      {TABS.map((tab) => {
        const active = tab.href !== null && tab.href === pathname;
        const className = active
          ? "flex flex-col items-center justify-center rounded-full bg-secondary-container px-5 py-1 text-on-secondary-container transition-transform duration-200 ease-out active:scale-90"
          : "flex flex-col items-center justify-center rounded-full px-5 py-1 text-on-surface-variant transition-colors hover:bg-surface-variant";
        const content = (
          <>
            <span className={`material-symbols-outlined ${active ? "icon-fill" : ""}`}>{tab.icon}</span>
            <span className="mt-1 text-[14px] text-label-lg font-label-lg">{tab.label}</span>
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
