export type QuickButtonType = 'BTN_PRECEDENT' | 'BTN_CASES' | 'BTN_TRUST_TYPES';

export interface QuickButtonOption {
  id: QuickButtonType;
  label: string;
  description: string;
  presetQuery: string;
}

export interface DocumentCard {
  id: string;
  title: string;
  category: QuickButtonType;
  snippet: string;
  sourceUrl?: string;
}

export interface QuickPresetResponse {
  buttonType: QuickButtonType;
  presetQuery: string;
  documents: DocumentCard[];
}
