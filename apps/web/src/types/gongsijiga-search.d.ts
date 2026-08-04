declare module "gongsijiga-search" {
  export interface GongsijigaYear {
    year: number;
    price_per_sqm: number;
    notice_date: string;
    base_date?: string;
  }

  export interface GongsijigaResult {
    address: string;
    jibun: string;
    san: boolean;
    latest: GongsijigaYear;
    history: GongsijigaYear[];
    yoy_change_pct: number;
    source_url: string;
  }

  export function lookupGongsijiga(address: string): Promise<GongsijigaResult>;
}
