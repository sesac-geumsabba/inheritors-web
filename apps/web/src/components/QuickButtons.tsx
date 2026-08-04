'use client';

import React from 'react';

export type QuickButtonType = 'BTN_PRECEDENT' | 'BTN_CASES' | 'BTN_TRUST_TYPES';

export interface QuickButtonOption {
  id: QuickButtonType;
  label: string;
  description: string;
  preset_query: string;
}

export interface DocumentCard {
  id: string;
  title: string;
  category: QuickButtonType;
  snippet: string;
  source_url?: string;
}

export interface QuickPresetResponse {
  button_type: QuickButtonType;
  preset_query: string;
  documents: DocumentCard[];
}

interface QuickButtonsProps {
  onSelectPreset: (presetQuery: string, documents: DocumentCard[]) => void;
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
}

const BUTTON_OPTIONS: QuickButtonOption[] = [
  {
    id: 'BTN_PRECEDENT',
    label: '⚖️ 대표 판례',
    description: '유류분 반환 청구 및 유언대용신탁 관련 핵심 법원 판례',
    preset_query: '유언대용신탁과 유류분 반환 청구 관련 대표 판례를 알려주세요.',
  },
  {
    id: 'BTN_CASES',
    label: '💡 실생활 사례',
    description: '자녀 간 상속 분쟁 예방 및 실생활 신탁 활용 사례',
    preset_query: '시니어 자산가가 자녀 간 상속 분쟁을 예방하기 위해 신탁을 활용한 실생활 사례를 보여주세요.',
  },
  {
    id: 'BTN_TRUST_TYPES',
    label: '📜 신탁 특약 종류',
    description: '유언대용신탁의 맞춤형 특약 유형 안내',
    preset_query: '유언대용신탁에서 설정할 수 있는 주요 특약 종류에는 무엇이 있나요?',
  },
];

export const QuickButtons: React.FC<QuickButtonsProps> = ({
  onSelectPreset,
  isLoading,
  setIsLoading,
}) => {
  const handleButtonClick = async (option: QuickButtonOption) => {
    if (isLoading) return;
    setIsLoading(true);
    try {
      const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:8000';
      const res = await fetch(`${apiBaseUrl}/quick-buttons/${option.id}`);
      if (!res.ok) throw new Error('Quick button API fetch failed');
      const data: QuickPresetResponse = await res.json();
      onSelectPreset(data.preset_query, data.documents);
    } catch (err) {
      console.error(err);
      // Fallback local response
      onSelectPreset(option.preset_query, []);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="quick-buttons-container">
      <h3 className="quick-buttons-title">궁금한 주제를 선택해보세요 (Quick 추천)</h3>
      <div className="quick-buttons-grid">
        {BUTTON_OPTIONS.map((opt) => (
          <button
            key={opt.id}
            onClick={() => handleButtonClick(opt)}
            disabled={isLoading}
            className="quick-button-item"
          >
            <div className="quick-button-label">{opt.label}</div>
            <div className="quick-button-desc">{opt.description}</div>
          </button>
        ))}
      </div>
    </div>
  );
};
