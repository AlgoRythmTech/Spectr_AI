import React from 'react';

const SECTION_ICONS = {
  'ISSUE IDENTIFIED': { color: '#1A1A2E', symbol: '\u25C8' },
  'APPLICABLE LAW': { color: '#1A1A2E', symbol: '\u25B8' },
  'CASE LAW': { color: '#1A1A2E', symbol: '\u25B8' },
  'ANALYSIS': { color: '#1A1A2E', symbol: '\u25B8' },
  'FINANCIAL EXPOSURE': { color: '#B45309', symbol: '\u25B8' },
  'RECOMMENDATION': { color: '#166534', symbol: '\u25B8' },
  'RESPONSE': { color: '#1A1A2E', symbol: '\u25B8' },
};

function getSectionMeta(title) {
  const upper = title.toUpperCase();
  for (const [key, val] of Object.entries(SECTION_ICONS)) {
    if (upper.includes(key)) return { ...val, label: key };
  }
  return { color: '#1A1A2E', symbol: '\u25B8', label: title.toUpperCase() };
}

function formatContent(content) {
  if (!content) return null;
  
  const lines = content.split('\n');
  return lines.map((line, i) => {
    const trimmed = line.trim();
    if (!trimmed) return <br key={i} />;
    
    // Bold text **text**
    const parts = trimmed.split(/(\*\*[^*]+\*\*)/g);
    const rendered = parts.map((part, j) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={j} className="font-semibold text-[#0D0D0D]">{part.slice(2, -2)}</strong>;
      }
      return part;
    });
    
    // Check if it's a citation line (contains section references or case names)
    const isCitation = /Section\s+\d+|Act[,\s]|\d{4}\s*(SC|SCC|AIR)|\|\s*\d{4}\s*\|/.test(trimmed);
    const isMoney = /₹[\d,]+|TOTAL|EXPOSURE|Principal|Interest|Penalty/.test(trimmed);
    
    if (isMoney) {
      return (
        <p key={i} className="font-mono text-[13px] leading-6 text-[#0D0D0D] bg-[#FFF7ED] border-l-2 border-[#B45309] pl-3 py-1 my-1">
          {rendered}
        </p>
      );
    }
    
    if (isCitation) {
      return (
        <p key={i} className="font-mono text-[13px] leading-6 text-[#4A4A4A] my-0.5">
          {rendered}
        </p>
      );
    }
    
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      return (
        <p key={i} className="text-[15px] leading-7 text-[#0D0D0D] pl-4 my-0.5 flex items-start gap-2">
          <span className="text-[#64748B] mt-1 text-xs">&#9656;</span>
          <span>{rendered.map((r, idx) => typeof r === 'string' ? r.replace(/^[-*]\s*/, '') : r)}</span>
        </p>
      );
    }
    
    return <p key={i} className="text-[15px] leading-7 text-[#0D0D0D] my-0.5">{rendered}</p>;
  });
}

export default function ResponseCard({ sections, sources, modelUsed, citationsCount, onExport, onDraft }) {
  if (!sections || sections.length === 0) return null;

  return (
    <div className="border border-[#E2E8F0] rounded-sm bg-white" data-testid="response-card">
      {sections.map((section, i) => {
        const meta = getSectionMeta(section.title);
        const isFinancial = section.title.toUpperCase().includes('FINANCIAL');
        const isRecommendation = section.title.toUpperCase().includes('RECOMMENDATION');
        
        return (
          <div
            key={i}
            className={`response-section border-b border-[#E2E8F0] last:border-b-0 p-5
              ${isFinancial ? 'bg-[#FFFBEB]' : ''} ${isRecommendation ? 'bg-[#F0FDF4]' : ''}`}
            data-testid={`response-section-${i}`}
          >
            <div className="flex items-center gap-2 mb-3">
              <span
                className="text-sm"
                style={{ color: meta.color }}
              >
                {meta.symbol}
              </span>
              <h3 className="text-xs font-bold tracking-widest uppercase" style={{ color: meta.color }}>
                {meta.label}
              </h3>
            </div>
            <div className="pl-5">
              {formatContent(section.content)}
            </div>
          </div>
        );
      })}
      
      {/* Footer with sources and actions */}
      <div className="px-5 py-3 bg-[#F8FAFC] border-t border-[#E2E8F0] flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-4 text-xs text-[#64748B]">
          {sources?.indiankanoon?.length > 0 && (
            <span className="font-mono">
              {sources.indiankanoon.length} judgments from IndianKanoon
            </span>
          )}
          {sources?.statutes_referenced && (
            <span className="font-mono">Statute DB referenced</span>
          )}
          {modelUsed && (
            <span className="font-mono text-[#94A3B8]">{modelUsed}</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {onExport && (
            <>
              <button
                onClick={() => onExport('docx')}
                className="text-xs font-medium text-[#4A4A4A] hover:text-[#0D0D0D] px-3 py-1.5 border border-[#E2E8F0] rounded-sm hover:bg-white transition-colors"
                data-testid="export-word-btn"
              >
                Word
              </button>
              <button
                onClick={() => onExport('pdf')}
                className="text-xs font-medium text-[#4A4A4A] hover:text-[#0D0D0D] px-3 py-1.5 border border-[#E2E8F0] rounded-sm hover:bg-white transition-colors"
                data-testid="export-pdf-btn"
              >
                PDF
              </button>
            </>
          )}
          {onDraft && (
            <button
              onClick={onDraft}
              className="text-xs font-medium text-white bg-[#1A1A2E] px-3 py-1.5 rounded-sm hover:bg-[#0D0D0D] transition-colors"
              data-testid="draft-this-btn"
            >
              Draft This
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
