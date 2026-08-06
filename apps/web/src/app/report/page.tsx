"use client";

import Link from "next/link";
import { Suspense, useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import TopAppBar from "@/components/TopAppBar";
import BottomNavBar from "@/components/BottomNavBar";

interface AssetItem {
  label: string;
  amount: string | null;
}

interface RiskItem {
  title: string;
  description: string;
}

interface ConsultationReport {
  summary: string;
  assets: AssetItem[];
  total_estimate: string | null;
  risks: RiskItem[];
  disclaimer: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

type Status = "loading" | "success" | "not_enough_turns" | "error" | "no_session";

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-[max(884px,100dvh)] bg-surface-container-lowest pb-[140px]">
      <TopAppBar />
      <main className="flex w-full flex-col gap-6 px-container-padding pt-[calc(56px+20px)]">
        {children}
      </main>
      <BottomNavBar />
    </div>
  );
}

function ReportPageInner() {
  const searchParams = useSearchParams();
  const sessionId = searchParams.get("session_id");
  const [status, setStatus] = useState<Status>(sessionId ? "loading" : "no_session");
  const [report, setReport] = useState<ConsultationReport | null>(null);
  const [minTurns, setMinTurns] = useState<number | null>(null);

  const fetchReport = useCallback(async () => {
    if (!sessionId) {
      setStatus("no_session");
      return;
    }
    setStatus("loading");
    try {
      const res = await fetch(`${API_BASE}/chat/${sessionId}/report`);
      if (res.status === 400) {
        const body = await res.json().catch(() => null);
        setMinTurns(body?.detail?.min_turns ?? null);
        setStatus("not_enough_turns");
        return;
      }
      if (!res.ok) throw new Error(`요청 실패 (${res.status})`);
      setReport((await res.json()) as ConsultationReport);
      setStatus("success");
    } catch {
      setStatus("error");
    }
  }, [sessionId]);

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  if (status === "no_session") {
    return (
      <Shell>
        <EmptyState
          title="아직 리포트를 만들 상담이 없어요"
          description="챗봇과 몇 차례 대화를 나누시면 상담 내용을 바탕으로 리포트를 만들어드려요."
          actionHref="/chat"
          actionLabel="상담하러 가기"
        />
      </Shell>
    );
  }

  if (status === "loading") {
    return (
      <Shell>
        <div className="flex flex-1 items-center justify-center py-24">
          <div className="flex items-center gap-2 text-on-surface-variant">
            <div className="h-2 w-2 animate-pulse rounded-full bg-brand-pink" />
            <div className="h-2 w-2 animate-pulse rounded-full bg-brand-pink delay-75" />
            <div className="h-2 w-2 animate-pulse rounded-full bg-brand-pink delay-150" />
            <span className="ml-2 text-body-md font-body-md">상담 내용을 정리하고 있어요...</span>
          </div>
        </div>
      </Shell>
    );
  }

  if (status === "not_enough_turns") {
    return (
      <Shell>
        <EmptyState
          title="조금 더 상담이 필요해요"
          description={
            minTurns
              ? `리포트를 만들려면 상담이 최소 ${minTurns}번 이상 오가야 해요. 계속 대화를 이어가 주세요.`
              : "상담 내용이 아직 리포트를 만들기엔 짧아요. 계속 대화를 이어가 주세요."
          }
          actionHref="/chat"
          actionLabel="상담 계속하기"
        />
      </Shell>
    );
  }

  if (status === "error") {
    return (
      <Shell>
        <EmptyState
          title="리포트를 불러오지 못했어요"
          description="일시적인 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
          onRetry={fetchReport}
        />
      </Shell>
    );
  }

  if (!report) return null;

  return (
    <Shell>
      <section>
        <h2 className="mb-2 text-headline-lg-mobile font-headline-lg-mobile text-on-surface">
          자산승계 리포트
        </h2>
        <p className="text-body-md font-body-md text-on-surface-variant">{report.summary}</p>
      </section>

      {report.assets.length > 0 && (
        <section className="rounded-2xl border border-outline-variant/30 bg-brand-pink-light p-6 shadow-sm">
          <h3 className="mb-6 flex items-center gap-2 text-label-lg font-label-lg text-brand-pink">
            <span className="material-symbols-outlined">account_balance</span>
            현재 자산 현황 요약
          </h3>
          <div className="flex flex-col gap-4">
            {report.assets.map((asset, i) => (
              <div
                key={i}
                className="flex items-center justify-between border-b border-outline-variant/20 pb-3"
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-surface-container-high text-on-surface-variant">
                    <span className="material-symbols-outlined">account_balance_wallet</span>
                  </div>
                  <span className="text-body-lg font-body-lg">{asset.label}</span>
                </div>
                {asset.amount && (
                  <span className="text-label-lg font-label-lg">{asset.amount}</span>
                )}
              </div>
            ))}
            {report.total_estimate && (
              <div className="flex items-center justify-between pt-2">
                <span className="text-body-lg font-body-lg text-on-surface-variant">총 추정 자산</span>
                <span className="text-headline-md font-headline-md text-brand-pink">
                  {report.total_estimate}
                </span>
              </div>
            )}
          </div>
        </section>
      )}

      {report.risks.length > 0 && (
        <section className="rounded-2xl border border-outline-variant/30 bg-brand-pink-light p-6 shadow-sm">
          <h3 className="mb-4 flex items-center gap-2 text-label-lg font-label-lg text-error">
            <span className="material-symbols-outlined">warning</span>
            법률적 위험 요소 (주의)
          </h3>
          <ul className="flex flex-col gap-4">
            {report.risks.map((risk, i) => (
              <li
                key={i}
                className="flex items-start gap-3 rounded-xl border border-outline-variant/30 bg-surface-container-lowest p-4 shadow-sm"
              >
                <span className="material-symbols-outlined icon-fill mt-0.5 text-error">warning</span>
                <div>
                  <strong className="mb-1 block text-label-lg font-label-lg">{risk.title}</strong>
                  <p className="text-body-md font-body-md text-on-surface-variant">
                    {risk.description}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      <p className="px-1 text-label-sm font-label-sm text-on-surface-variant opacity-70">
        {report.disclaimer}
      </p>

      <section>
        <button
          type="button"
          className="flex min-h-touch-target-min w-full items-center justify-center gap-2 rounded-full bg-brand-pink py-4 text-label-lg font-label-lg text-white shadow-sm transition-all hover:opacity-90 active:scale-95"
        >
          전문가 상담 연결하기
          <span className="material-symbols-outlined">arrow_forward</span>
        </button>
      </section>
    </Shell>
  );
}

function EmptyState({
  title,
  description,
  actionHref,
  actionLabel,
  onRetry,
}: {
  title: string;
  description: string;
  actionHref?: string;
  actionLabel?: string;
  onRetry?: () => void;
}) {
  return (
    <div className="flex flex-1 flex-col items-center gap-4 py-24 text-center">
      <span className="material-symbols-outlined text-[48px] text-on-surface-variant opacity-60">
        description
      </span>
      <div>
        <p className="mb-1 text-body-lg font-body-lg font-bold text-on-surface">{title}</p>
        <p className="text-body-md font-body-md text-on-surface-variant">{description}</p>
      </div>
      {actionHref && actionLabel && (
        <Link
          href={actionHref}
          className="rounded-full bg-brand-pink px-6 py-3 text-label-md font-label-md text-white transition-colors hover:opacity-90"
        >
          {actionLabel}
        </Link>
      )}
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="rounded-full border border-brand-pink px-6 py-3 text-label-md font-label-md text-brand-pink transition-colors hover:bg-brand-pink-light"
        >
          다시 시도
        </button>
      )}
    </div>
  );
}

export default function ReportPage() {
  // useSearchParams는 클라이언트에서 Suspense boundary가 필요하다(Next.js 요구사항).
  return (
    <Suspense
      fallback={
        <Shell>
          <div className="py-24" />
        </Shell>
      }
    >
      <ReportPageInner />
    </Suspense>
  );
}
