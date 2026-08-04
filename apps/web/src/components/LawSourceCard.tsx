import React from "react";

export interface LawSourceItem {
  source_type: "statute" | "case_law" | string;
  title: string;
  url?: string;
  snippet: string;
  score?: number;
  rank?: number;
}

interface LawSourceCardProps {
  source: LawSourceItem;
}

export const LawSourceCard: React.FC<LawSourceCardProps> = ({ source }) => {
  const isStatute = source.source_type === "statute";
  const badgeTextColor = isStatute
    ? "text-blue-600 dark:text-blue-400"
    : "text-purple-600 dark:text-purple-400";
  const badgeText = isStatute ? "[법령/조문]" : "[판례]";

  return (
    <div className="p-4 mb-3 border rounded-lg shadow-sm bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700">
      <div className="flex items-center justify-between mb-2">
        <span className={`text-xs font-semibold ${badgeTextColor}`}>
          {badgeText}
        </span>
        {source.rank && (
          <span className="text-xs text-gray-400">순위 #{source.rank}</span>
        )}
      </div>

      <h4 className="text-sm font-bold text-gray-900 dark:text-gray-100 mb-1">
        {source.title}
      </h4>

      <p className="text-xs text-gray-600 dark:text-gray-300 line-clamp-3 mb-2 leading-relaxed">
        {source.snippet}
      </p>

      {source.url && (
        <a
          href={source.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center text-xs font-medium text-blue-600 dark:text-blue-400 hover:underline"
        >
          원문 확인하기 &rarr;
        </a>
      )}
    </div>
  );
};

export default LawSourceCard;
