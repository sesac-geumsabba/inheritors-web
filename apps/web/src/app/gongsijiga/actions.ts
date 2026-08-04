"use server";

import { lookupGongsijiga, type GongsijigaResult } from "gongsijiga-search";

export type GongsijigaLookupState =
  | { ok: true; result: GongsijigaResult }
  | { ok: false; message: string };

export async function fetchGongsijiga(address: string): Promise<GongsijigaLookupState> {
  try {
    const result = await lookupGongsijiga(address);
    return { ok: true, result };
  } catch (err) {
    const message = err instanceof Error ? err.message : "공시지가 조회에 실패했습니다.";
    return { ok: false, message };
  }
}
