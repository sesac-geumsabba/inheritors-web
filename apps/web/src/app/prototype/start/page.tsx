"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import TopAppBar from "@/components/TopAppBar";
import BottomNavBar from "@/components/BottomNavBar";

export default function PrototypeStartPage() {
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const [easedProgress, setEasedProgress] = useState(0);

  useEffect(() => {
    const scrollArea = scrollAreaRef.current;
    if (!scrollArea) return;

    const smoothstep = (min: number, max: number, value: number) => {
      const x = Math.max(0, Math.min(1, (value - min) / (max - min)));
      return x * x * (3 - 2 * x);
    };

    const handleScroll = () => {
      const maxScroll = window.innerHeight * 0.5;
      const progress = Math.min(1, Math.max(0, scrollArea.scrollTop / maxScroll));
      setEasedProgress(smoothstep(0, 1, progress));
    };

    scrollArea.addEventListener("scroll", handleScroll);
    return () => scrollArea.removeEventListener("scroll", handleScroll);
  }, []);

  const currentPadding = 16 * (1 - easedProgress);
  const currentRadius = 16 * (1 - easedProgress);
  const mediaBg = easedProgress > 0.8 ? "#F52D81" : "transparent";
  const titleOpacity = easedProgress > 0.5 ? (easedProgress - 0.5) * 2 : 0;
  const titleTranslateY = 20 * (1 - titleOpacity);
  const hintOpacity = 1 - easedProgress * 2;

  return (
    <div className="relative mx-auto flex h-[100dvh] w-full max-w-[480px] flex-col overflow-hidden border-x border-outline-variant/30 bg-surface shadow-2xl">
      <TopAppBar />

      <main
        ref={scrollAreaRef}
        className="relative z-0 flex flex-1 flex-col overflow-y-auto scroll-smooth pt-16 pb-24"
      >
        <div ref={containerRef} className="relative mb-8 h-[120vh]">
          <div className="sticky top-0 flex h-[calc(100dvh-160px)] items-center justify-center overflow-hidden">
            <div
              className="flex h-full w-full flex-col p-4"
              style={{ padding: `${currentPadding}px` }}
            >
              <div
                className="relative z-1 flex flex-1 items-center justify-center overflow-hidden border border-outline-variant/20 bg-brand-pink-light shadow-sm transition-colors duration-150"
                style={{
                  borderRadius: `${currentRadius}px`,
                  backgroundColor: `rgba(253, 232, 240, ${1 - easedProgress})`,
                  padding: `${32 * (1 - easedProgress)}px`,
                }}
              >
                <div
                  className="flex h-full w-full items-center justify-center bg-white shadow-inner"
                  style={{ borderRadius: `${currentRadius * 0.75}px` }}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src="https://lh3.googleusercontent.com/aida/AP1WRLvJ6tEPAwMTmzv4We3wgvUD4LXN6t53JCADrSxH21ILNyvtJGmT2nAfbtDbp31i1yPPp-X7vCaXCC35D_dqI78WFQ6AdyJrBBmPZEScDadJ7g2A_sPWersSR0jRXclHAdLSA2LPxjOIWM3Bwd8WUmanFX5ZEJn5zpgoiRzsh4V2VKLNtl_yo0aOItobqmFP-n3dsY6LZj7ua_-w0XV9QO0WhTVAi9xtMYJ_u1IOec-Hya-nS2w8gRQC4rlrVaoIcaP2zwCLos5U"
                    alt="안전하고 편안한 상속 준비"
                    className="h-full w-full object-contain p-4 transition-transform duration-150"
                    style={{
                      backgroundColor: mediaBg,
                      transform: `scale(${1 + easedProgress * 0.1})`,
                    }}
                  />
                </div>
              </div>
            </div>

            <div className="pointer-events-none absolute left-0 top-0 z-10 flex h-full w-full flex-col items-center justify-center">
              <h2
                className="px-4 text-center font-bold text-white text-headline-md shadow-sm transition-all duration-200"
                style={{
                  opacity: titleOpacity,
                  transform: `translateY(${titleTranslateY}px)`,
                }}
              >
                안전하고 편안한 상속 준비
              </h2>
            </div>

            <div
              className="absolute bottom-8 flex flex-col items-center text-on-surface-variant transition-opacity duration-200"
              style={{ opacity: Math.max(0, hintOpacity) }}
            >
              <span className="mb-1 text-sm font-medium">스크롤해서 확인하기</span>
              <span className="material-symbols-outlined animate-bounce">
                keyboard_arrow_down
              </span>
            </div>
          </div>
        </div>

        <div className="px-container-padding pb-32">
          <div className="z-1 flex flex-col items-center justify-center gap-4 rounded-2xl border border-outline-variant/20 bg-brand-pink-light/50 p-6 text-center shadow-sm">
            <h1 className="text-headline-md font-headline-md text-on-surface">안녕하세요!</h1>
            <p className="text-body-lg font-body-lg text-on-surface-variant">
              안전하고 편안한 상속 준비,
              <br />
              <span className="font-bold text-[#F52D81]">상속자들이 도와드릴게요.</span>
            </p>
          </div>
        </div>
      </main>

      <div className="absolute bottom-[72px] left-0 z-10 w-full bg-gradient-to-t from-surface via-surface to-transparent px-container-padding pt-4 pb-4">
        <Link
          href="/chat"
          className="group flex min-h-[56px] w-full items-center justify-center gap-2 rounded-lg bg-[#F52D81] px-4 py-3 text-label-lg font-label-lg text-white shadow-md transition-all hover:opacity-90 active:scale-[0.98]"
        >
          <span>시작하기</span>
          <span className="material-symbols-outlined transition-transform group-hover:translate-x-1">
            arrow_forward
          </span>
        </Link>
      </div>

      <BottomNavBar />
    </div>
  );
}
