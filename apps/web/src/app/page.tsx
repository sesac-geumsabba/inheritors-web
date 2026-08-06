"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef } from "react";

export default function OnboardingPage() {
  const router = useRouter();
  const scrollRef = useRef<HTMLDivElement>(null);
  const cardFrameRef = useRef<HTMLDivElement>(null);
  const mediaCardRef = useRef<HTMLDivElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const mediaRef = useRef<HTMLImageElement>(null);
  const hintRef = useRef<HTMLDivElement>(null);

  const smoothstep = (min: number, max: number, value: number) => {
    const x = Math.max(0, Math.min(1, (value - min) / (max - min)));
    return x * x * (3 - 2 * x);
  };

  const updateAnimation = useCallback(() => {
    const scrollArea = scrollRef.current;
    if (!scrollArea) return;

    const scrollOffset = scrollArea.scrollTop;
    const maxScroll = window.innerHeight * 0.5;
    const progress = Math.min(1, Math.max(0, scrollOffset / maxScroll));
    const easedProgress = smoothstep(0, 1, progress);

    const cardFrame = cardFrameRef.current;
    const mediaCard = mediaCardRef.current;
    const wrapper = wrapperRef.current;
    const media = mediaRef.current;
    const hint = hintRef.current;

    if (!cardFrame || !mediaCard || !wrapper || !media || !hint) return;

    if (easedProgress > 0) {
      const currentPadding = 16 * (1 - easedProgress);
      cardFrame.style.padding = `${currentPadding}px`;

      const currentRadius = 16 * (1 - easedProgress);
      mediaCard.style.borderRadius = `${currentRadius}px`;
      wrapper.style.borderRadius = `${currentRadius * 0.75}px`;

      const alpha = 1 - easedProgress;
      mediaCard.style.borderColor = `rgba(226, 189, 197, ${0.2 * alpha})`;
      mediaCard.style.padding = `${32 * alpha}px`;

      if (easedProgress > 0.8) {
        media.style.objectFit = "cover";
        media.style.padding = "0";
        media.style.backgroundColor = "#F52D81";
      } else {
        media.style.objectFit = "contain";
        media.style.padding = `${16 * alpha}px`;
        media.style.backgroundColor = "transparent";
      }

      const scale = 1 + easedProgress * 0.1;
      media.style.transform = `scale(${scale})`;

      hint.style.opacity = String(Math.max(0, 1 - easedProgress * 2));
    } else {
      cardFrame.style.padding = "1rem";
      mediaCard.style.borderRadius = "1rem";
      mediaCard.style.borderColor = "rgba(226, 189, 197, 0.2)";
      mediaCard.style.padding = "2rem";
      wrapper.style.borderRadius = "0.75rem";
      media.style.objectFit = "contain";
      media.style.padding = "1rem";
      media.style.backgroundColor = "transparent";
      media.style.transform = "scale(1)";
      hint.style.opacity = "1";
    }
  }, []);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const handler = () => requestAnimationFrame(updateAnimation);
    el.addEventListener("scroll", handler, { passive: true });
    updateAnimation();
    return () => el.removeEventListener("scroll", handler);
  }, [updateAnimation]);

  function handleStart() {
    router.push("/chat");
  }

  return (
    <>
      {/* 데스크톱/모바일 공통 폭 고정 프레임은 layout.tsx가 제공(iPhone 14 Pro Max 430px) —
          여기선 그 프레임 안에서 온보딩 화면 자체의 h-[100dvh] 레이아웃만 관리한다. */}
      <div className="relative flex h-[100dvh] w-full flex-col overflow-hidden bg-surface">
        {/* TopAppBar */}
          <header className="z-20 flex h-touch-target-min w-full shrink-0 items-center border-b border-outline-variant bg-surface px-container-padding">
            <span className="flex-1 truncate text-headline-md font-headline-md font-bold text-brand-pink">
              상속자들
            </span>
          </header>

          {/* 스크롤 영역 */}
          <main
            ref={scrollRef}
            className="relative z-0 flex flex-1 flex-col overflow-y-auto scroll-smooth"
          >
            {/* ScrollExpand 섹션 */}
            <div className="relative" style={{ height: "150vh" }}>
              <div
                className="sticky flex items-center justify-center overflow-hidden"
                style={{
                  top: "56px",
                  height: "calc(100vh - 56px - 88px)",
                }}
              >
                {/* 카드 프레임 */}
                <div
                  ref={cardFrameRef}
                  className="flex h-full w-full flex-col"
                  style={{ padding: "1rem" }}
                >
                  <div
                    ref={mediaCardRef}
                    className="relative z-[1] flex flex-1 items-center justify-center overflow-hidden border border-outline-variant/20 shadow-sm"
                    style={{ borderRadius: "1rem", padding: "2rem" }}
                  >
                    <div
                      ref={wrapperRef}
                      className="relative flex h-full w-full items-center justify-center bg-white shadow-inner"
                      style={{ borderRadius: "0.75rem" }}
                    >
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        ref={mediaRef}
                        src="/mascot/neuri.png"
                        alt="안전하고 편안한 상속 준비"
                        className="h-full w-full"
                        style={{
                          objectFit: "contain",
                          padding: "1rem",
                          backgroundColor: "transparent",
                          willChange: "transform",
                          transformOrigin: "center center",
                          transition: "none",
                        }}
                      />
                    </div>
                  </div>
                </div>

                {/* 스크롤 힌트 */}
                <div
                  ref={hintRef}
                  className="absolute bottom-8 flex flex-col items-center text-on-surface-variant"
                  style={{ animation: "ob-bounce 2s infinite" }}
                >
                  <span className="mb-1 text-sm font-medium">스크롤해서 확인하기</span>
                  <span className="material-symbols-outlined">keyboard_arrow_down</span>
                </div>
              </div>
            </div>

            {/* 환영 텍스트 */}
            <div className="px-container-padding pb-32">
              <div className="flex flex-col justify-center gap-4 rounded-2xl border border-outline-variant/20 bg-brand-pink-light/50 p-6 text-center shadow-sm">
                <h1 className="text-headline-md font-headline-md text-on-surface">
                  안녕하세요!
                </h1>
                <p className="text-body-lg font-body-lg text-on-surface-variant">
                  안전하고 편안한 상속 준비,
                  <br />
                  <span className="font-bold text-brand-pink">상속자들이 도와드릴게요.</span>
                </p>
              </div>
            </div>
          </main>

          {/* 하단 CTA */}
          <div className="absolute bottom-0 left-0 z-10 w-full bg-gradient-to-t from-surface via-surface to-transparent px-0 pb-container-padding pt-4">
            <button
              type="button"
              onClick={handleStart}
              className="group flex h-touch-target-min w-full items-center justify-center gap-2 rounded-full bg-brand-pink text-label-lg font-label-lg font-bold text-white shadow-md transition-all hover:opacity-90 active:scale-[0.98]"
            >
              시작하기
              <span className="material-symbols-outlined transition-transform group-hover:translate-x-1">
                arrow_forward
              </span>
            </button>
          </div>
      </div>

      <style>{`
        @keyframes ob-bounce {
          0%, 20%, 50%, 80%, 100% { transform: translateY(0); }
          40% { transform: translateY(-10px); }
          60% { transform: translateY(-5px); }
        }
      `}</style>
    </>
  );
}
