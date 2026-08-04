"use client";

import { useState, type FormEvent } from "react";
import { fetchGongsijiga, type GongsijigaLookupState } from "./actions";

export default function GongsijigaSearch() {
  const [address, setAddress] = useState("");
  const [state, setState] = useState<GongsijigaLookupState | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);
    setState(await fetchGongsijiga(address));
    setLoading(false);
  }

  return (
    <div>
      <form onSubmit={handleSubmit}>
        <input
          value={address}
          onChange={(e) => setAddress(e.target.value)}
          placeholder="예: 서울특별시 강남구 역삼동 736"
        />
        <button type="submit" disabled={loading || !address}>
          {loading ? "조회 중..." : "공시지가 조회"}
        </button>
      </form>

      {state && !state.ok && <p role="alert">{state.message}</p>}

      {state?.ok && (
        <dl>
          <dt>{state.result.latest.year}년 개별공시지가 (㎡당)</dt>
          <dd>{state.result.latest.price_per_sqm.toLocaleString()}원</dd>
          <dt>전년 대비</dt>
          <dd>{state.result.yoy_change_pct}%</dd>
        </dl>
      )}
    </div>
  );
}
