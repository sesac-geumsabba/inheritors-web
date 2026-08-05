"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

interface TabItem {
  href: string | null;
  label: string;
  icon: string;
}

const TABS: readonly TabItem[] = [
  { href: "/prototype/start", label: "내 정보", icon: "person" },
  { href: "/chat", label: "챗봇", icon: "chat" },
  { href: "/prototype/report", label: "리포트", icon: "description" },
  { href: "action:back", label: "뒤로가기", icon: "arrow_back" },
];

export default function BottomNavBar() {
  const pathname = usePathname();
  const router = useRouter();

  return (
    <nav className="fixed bottom-0 left-0 z-50 flex h-[72px] w-full items-center justify-around rounded-t-xl border-t border-outline-variant/50 bg-surface px-2 py-2 shadow-[0_-2px_10px_rgba(0,0,0,0.05)]">
      {TABS.map((tab) => {
        const active = tab.href !== null && tab.href === pathname;
        const className = active
          ? "flex h-full w-[64px] shrink-0 scale-95 flex-col items-center justify-center rounded-xl bg-[#f52d81] px-2 py-1 text-white transition-transform duration-200"
          : "flex h-full flex-1 flex-col items-center justify-center rounded-xl px-2 py-1 text-on-surface-variant transition-colors hover:bg-surface-container-high";
        
        const content = (
          <>
            <span className={`material-symbols-outlined mb-1 ${active ? "icon-fill" : ""}`}>
              {tab.icon}
            </span>
            <span className={`font-label-sm text-[12px] whitespace-nowrap ${active ? "font-bold" : ""}`}>
              {tab.label}
            </span>
          </>
        );

        if (tab.href === "action:back") {
          return (
            <button
              key={tab.label}
              type="button"
              onClick={() => router.back()}
              className={className}
            >
              {content}
            </button>
          );
        }

        if (tab.href) {
          return (
            <Link key={tab.label} href={tab.href} className={className}>
              {content}
            </Link>
          );
        }

        return (
          <button key={tab.label} type="button" className={className}>
            {content}
          </button>
        );
      })}
    </nav>
  );
}
