'use client';

import React from 'react';
import { DocumentCard } from './QuickButtons';

interface DocumentCardListProps {
  documents: DocumentCard[];
  isLoading: boolean;
}

export const DocumentCardList: React.FC<DocumentCardListProps> = ({
  documents,
  isLoading,
}) => {
  if (isLoading) {
    return (
      <div className="skeleton-loader-container">
        <div className="skeleton-card">
          <div className="skeleton-line skeleton-title"></div>
          <div className="skeleton-line skeleton-body"></div>
          <div className="skeleton-line skeleton-body short"></div>
        </div>
        <div className="skeleton-card">
          <div className="skeleton-line skeleton-title"></div>
          <div className="skeleton-line skeleton-body"></div>
          <div className="skeleton-line skeleton-body short"></div>
        </div>
      </div>
    );
  }

  if (!documents || documents.length === 0) {
    return null;
  }

  return (
    <div className="document-card-list">
      <h4 className="document-list-title">📌 추천 관련 자료</h4>
      <div className="document-cards-grid">
        {documents.map((doc) => (
          <div key={doc.id} className="document-card">
            <h5 className="document-card-title">{doc.title}</h5>
            <p className="document-card-snippet">{doc.snippet}</p>
            {doc.source_url && (
              <a
                href={doc.source_url}
                target="_blank"
                rel="noreferrer"
                className="document-card-link"
              >
                원문 보기 ↗
              </a>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
