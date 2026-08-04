"use client";

import { useEffect, useState } from "react";

const HIDDEN_UNTIL_KEY = "onboarding-hidden-until";
const HIDE_DURATION_MS = 24 * 60 * 60 * 1000;

function isCurrentlyHidden(): boolean {
  const hiddenUntil = Number(localStorage.getItem(HIDDEN_UNTIL_KEY));
  return Boolean(hiddenUntil) && Date.now() < hiddenUntil;
}

export default function OnboardingModal() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!isCurrentlyHidden()) setOpen(true);
  }, []);

  function hideForToday() {
    localStorage.setItem(HIDDEN_UNTIL_KEY, String(Date.now() + HIDE_DURATION_MS));
    setOpen(false);
  }

  return (
    <>
      <button type="button" onClick={() => setOpen(true)}>
        서비스 안내
      </button>

      {open && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="onboarding-title"
          style={{
            position: "fixed",
            inset: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "rgba(0, 0, 0, 0.5)",
          }}
        >
          <div
            style={{
              background: "white",
              borderRadius: 8,
              padding: 24,
              maxWidth: 420,
            }}
          >
            <h2 id="onboarding-title">유언대용신탁이 처음이신가요?</h2>
            <p>
              살아계실 땐 월세 받으시고, 사후엔 자녀에게 안전하게 전달되는
              <br />
              &ldquo;통장 잠금장치&rdquo;라고 생각하시면 됩니다.
            </p>
            <p>
              신탁회사가 자산을 안전하게 관리하다가 미리 정해두신 방식대로
              자녀에게 전달해드립니다. 유언장과 달리 생전에도 수익을 받으실 수
              있고, 분쟁 없이 정확하게 전달됩니다.
            </p>
            <button type="button" onClick={() => setOpen(false)}>
              확인
            </button>
            <button type="button" onClick={hideForToday}>
              오늘 하루 보지 않기
            </button>
          </div>
        </div>
      )}
    </>
  );
}
