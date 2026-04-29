import React, { useState, useMemo } from 'react';
import { FileDown, Edit3, Eye, EyeOff, Scale, Copy, Check, AlertTriangle, FileText, Table2, Gavel, FileWarning, ChevronDown } from 'lucide-react';
import CitationPanel from './CitationPanel';
import RiskExposureCard, { parseRiskAnalysis, stripRiskAnalysis } from './RiskExposureCard';

/**
 * Markdown renderer for Spectr AI responses.
 */
function renderMarkdownContent(content, citations, onCitationClick) {
  if (!content) return null;
  const lines = String(content).split('\n');
  const elements = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    if (!trimmed) { elements.push(<div key={i} style={{ height: 8 }} />); i++; continue; }

    if (/^---+$/.test(trimmed) || /^\*\*\*+$/.test(trimmed)) {
      elements.push(<hr key={i} style={{ border: 'none', borderTop: '1px solid #EBEBEB', margin: '16px 0' }} />);
      i++; continue;
    }

    // Table
    if (trimmed.startsWith('|')) {
      const tableLines = [];
      while (i < lines.length && lines[i].trim().startsWith('|')) { tableLines.push(lines[i].trim()); i++; }
      elements.push(renderTable(tableLines, elements.length));
      continue;
    }

    // Code block
    if (trimmed.startsWith('```')) {
      const codeLines = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith('```')) { codeLines.push(lines[i]); i++; }
      i++;
      elements.push(
        <pre key={elements.length} style={{
          background: '#111', color: '#E2E8F0', padding: '16px 20px',
          borderRadius: 12, fontSize: 13, lineHeight: 1.7, overflowX: 'auto',
          fontFamily: "'IBM Plex Mono', monospace", margin: '12px 0',
        }}>
          {codeLines.join('\n')}
        </pre>
      );
      continue;
    }

    // Headers
    if (trimmed.startsWith('#### ') || trimmed.startsWith('##### ')) {
      elements.push(
        <h5 key={i} style={{ fontSize: 13, fontWeight: 700, color: '#374151', marginTop: 18, marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.02em' }}>
          {renderInline(trimmed.replace(/^#+\s/, ''), citations, onCitationClick)}
        </h5>
      );
      i++; continue;
    }
    if (trimmed.startsWith('### ')) {
      elements.push(
        <h4 key={i} style={{ fontFamily: "'Inter', sans-serif", fontSize: 14.5, fontWeight: 700, color: '#0A0A0A', marginTop: 24, marginBottom: 8, paddingBottom: 6, borderBottom: '1px solid #F0F0F0', letterSpacing: '-0.01em' }}>
          {renderInline(trimmed.slice(4), citations, onCitationClick)}
        </h4>
      );
      i++; continue;
    }
    if (trimmed.startsWith('## ')) {
      elements.push(
        <h3 key={i} style={{ fontFamily: "'Inter', sans-serif", letterSpacing: '-0.05em', fontSize: 19, fontWeight: 600, color: '#0A0A0A', marginTop: 28, marginBottom: 8, letterSpacing: '-0.015em', lineHeight: 1.25 }}>
          {renderInline(trimmed.slice(3), citations, onCitationClick)}
        </h3>
      );
      i++; continue;
    }
    if (trimmed.startsWith('# ')) {
      elements.push(
        <h2 key={i} style={{ fontFamily: "'Inter', sans-serif", letterSpacing: '-0.05em', fontSize: 24, fontWeight: 600, color: '#0A0A0A', marginTop: 32, marginBottom: 10, letterSpacing: '-0.015em', lineHeight: 1.2 }}>
          {renderInline(trimmed.slice(2), citations, onCitationClick)}
        </h2>
      );
      i++; continue;
    }

    // Blockquote — with special treatment for KILL-SHOT and KEY callouts
    // KILL-SHOT: bold black left bar, slightly larger type, no italic (it's
    // the ratio that ends the argument — this is the pullquote of the memo)
    // KEY: amber left bar, subtly highlighted background, normal type
    // Research Provenance: tiny muted italics at the very bottom
    // Everything else: standard grey blockquote
    if (trimmed.startsWith('> ')) {
      const quoteLines = [];
      while (i < lines.length && lines[i].trim().startsWith('> ')) { quoteLines.push(lines[i].trim().slice(2)); i++; }
      const joined = quoteLines.join(' ');
      const upper = joined.toUpperCase();

      if (upper.includes('KILL-SHOT') || upper.includes('KILLSHOT')) {
        elements.push(
          <div key={elements.length} style={{
            borderLeft: '3px solid #0A0A0A',
            background: 'linear-gradient(90deg, rgba(10,10,10,0.04) 0%, rgba(10,10,10,0) 60%)',
            padding: '14px 18px',
            margin: '18px 0',
            borderRadius: '0 8px 8px 0',
            fontSize: 15,
            lineHeight: 1.6,
            color: '#0A0A0A',
            fontWeight: 500,
          }}>
            {quoteLines.map((ql, qi) => <p key={qi} style={{ margin: '4px 0' }}>{renderInline(ql, citations, onCitationClick)}</p>)}
          </div>
        );
        continue;
      }

      if (upper.startsWith('**KEY:') || upper.startsWith('KEY:') || upper.includes('**KEY:**')) {
        elements.push(
          <div key={elements.length} style={{
            borderLeft: '3px solid #D97706',
            background: 'rgba(217, 119, 6, 0.05)',
            padding: '11px 16px',
            margin: '12px 0',
            borderRadius: '0 6px 6px 0',
            fontSize: 14,
            lineHeight: 1.65,
            color: '#1A1A1A',
          }}>
            {quoteLines.map((ql, qi) => <p key={qi} style={{ margin: '3px 0' }}>{renderInline(ql, citations, onCitationClick)}</p>)}
          </div>
        );
        continue;
      }

      if (upper.includes('RESEARCH RUN:') || upper.includes('AI-ASSISTED RESEARCH') || upper.includes('SPECTR & CO')) {
        elements.push(
          <div key={elements.length} style={{
            borderTop: '1px solid rgba(0,0,0,0.04)',
            marginTop: 20, paddingTop: 12, paddingBottom: 2,
            fontSize: 11,
            lineHeight: 1.55,
            color: '#9AA0A6',
            fontStyle: 'italic',
          }}>
            {quoteLines.map((ql, qi) => <p key={qi} style={{ margin: '2px 0' }}>{renderInline(ql, citations, onCitationClick)}</p>)}
          </div>
        );
        continue;
      }

      // Default blockquote
      elements.push(
        <blockquote key={elements.length} style={{
          borderLeft: '2px solid #D1D5DB', paddingLeft: 14, margin: '10px 0',
          color: '#4B5563', fontStyle: 'italic', fontSize: 14, lineHeight: 1.7,
        }}>
          {quoteLines.map((ql, qi) => <p key={qi} style={{ margin: '3px 0' }}>{renderInline(ql, citations, onCitationClick)}</p>)}
        </blockquote>
      );
      continue;
    }

    // Warning callout
    if (trimmed.startsWith('⚠️') || trimmed.includes('WARNING') || trimmed.includes('CAUTION')) {
      elements.push(
        <div key={i} style={{
          background: '#F5F5F5', border: '1px solid #E5E5E5', borderRadius: 8,
          padding: '10px 14px', margin: '8px 0', fontSize: 13, lineHeight: 1.6,
          display: 'flex', alignItems: 'flex-start', gap: 8,
        }}>
          <AlertTriangle style={{ width: 14, height: 14, color: '#000', flexShrink: 0, marginTop: 2 }} />
          <span>{renderInline(trimmed, citations, onCitationClick)}</span>
        </div>
      );
      i++; continue;
    }

    // Bullet points
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      elements.push(
        <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 8, margin: '3px 0', paddingLeft: 2 }}>
          <span style={{ color: '#999', fontSize: 5, marginTop: 9, flexShrink: 0 }}>●</span>
          <p style={{ fontSize: 14.5, lineHeight: 1.75, color: '#1A1A1A', margin: 0 }}>
            {renderInline(trimmed.replace(/^[-*]\s*/, ''), citations, onCitationClick)}
          </p>
        </div>
      );
      i++; continue;
    }

    // Sub-bullets
    if (line.startsWith('  - ') || line.startsWith('  * ') || line.startsWith('    - ')) {
      elements.push(
        <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 8, margin: '2px 0', paddingLeft: 24 }}>
          <span style={{ color: '#CCC', fontSize: 4, marginTop: 9, flexShrink: 0 }}>○</span>
          <p style={{ fontSize: 13, lineHeight: 1.7, color: '#4B5563', margin: 0 }}>
            {renderInline(trimmed.replace(/^[-*]\s*/, ''), citations, onCitationClick)}
          </p>
        </div>
      );
      i++; continue;
    }

    // Numbered items
    if (/^\d+\.\s/.test(trimmed)) {
      const num = trimmed.match(/^(\d+)\./)[1];
      elements.push(
        <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 10, margin: '4px 0' }}>
          <span style={{ fontSize: 13, fontWeight: 700, color: '#0A0A0A', fontFamily: 'monospace', marginTop: 2, flexShrink: 0, minWidth: 20, textAlign: 'right' }}>{num}.</span>
          <p style={{ fontSize: 14.5, lineHeight: 1.75, color: '#1A1A1A', margin: 0 }}>
            {renderInline(trimmed.replace(/^\d+\.\s*/, ''), citations, onCitationClick)}
          </p>
        </div>
      );
      i++; continue;
    }

    // Default paragraph
    elements.push(
      <p key={i} style={{ fontSize: 14.5, lineHeight: 1.75, color: '#1A1A1A', margin: '2px 0' }}>
        {renderInline(trimmed, citations, onCitationClick)}
      </p>
    );
    i++;
  }

  return elements;
}

// Urgency-tag visual config. The prompt emits `[CRITICAL]`, `[URGENT]`, `[KEY]`
// at the start of Action Items and (sparingly) inline in Bottom Line / KEY
// callouts. These patterns get a colored pill + underline on the sentence that
// follows, so a client scanning the memo sees what will hurt them first.
const URGENCY_TAGS = {
  '[CRITICAL]': {
    label: 'CRITICAL',
    pillBg: '#FEF2F2',
    pillFg: '#B91C1C',
    pillBorder: '#FECACA',
    underline: '#DC2626',
  },
  '[URGENT]': {
    label: 'URGENT',
    pillBg: '#FFFBEB',
    pillFg: '#B45309',
    pillBorder: '#FDE68A',
    underline: '#D97706',
  },
  '[KEY]': {
    label: 'KEY',
    pillBg: '#F5F5F5',
    pillFg: '#1F2937',
    pillBorder: '#E5E7EB',
    underline: '#6B7280',
  },
};

function renderInline(text, citations, onCitationClick) {
  if (!text) return null;

  let parts = [text];

  // Urgency tag handling — run FIRST so the tag + the rest of the line can
  // be styled together. Pattern: line starts with [CRITICAL] / [URGENT] / [KEY]
  // followed by a space. We render a small pill for the tag and underline the
  // remainder of the line in the matching color.
  parts = parts.flatMap(part => {
    if (typeof part !== 'string') return [part];
    for (const tag of Object.keys(URGENCY_TAGS)) {
      if (part.trimStart().startsWith(tag + ' ')) {
        const cfg = URGENCY_TAGS[tag];
        // Preserve any leading whitespace from the numbered-list indent
        const leading = part.match(/^\s*/)[0];
        const rest = part.trimStart().slice(tag.length + 1);
        return [
          leading,
          <span key={`tag-${tag}`} style={{
            display: 'inline-block',
            fontSize: 10,
            fontWeight: 700,
            letterSpacing: '0.04em',
            padding: '2.5px 8px',
            marginRight: 8,
            borderRadius: 4,
            background: cfg.pillBg,
            color: cfg.pillFg,
            border: `1px solid ${cfg.pillBorder}`,
            verticalAlign: 'baseline',
            // Subtle outer glow so CRITICAL items jump off the scan line
            boxShadow: tag === '[CRITICAL]'
              ? `0 0 0 2px ${cfg.pillBg}, 0 1px 4px rgba(220, 38, 38, 0.18)`
              : tag === '[URGENT]'
              ? `0 1px 3px rgba(217, 119, 6, 0.14)`
              : 'none',
          }}>{cfg.label}</span>,
          <span key={`urgent-body-${tag}`} style={{
            textDecoration: 'underline',
            textDecorationColor: cfg.underline,
            textDecorationThickness: '2px',
            textUnderlineOffset: '3px',
          }}>{rest}</span>,
        ];
      }
    }
    return [part];
  });

  if (citations && citations.length > 0) {
    citations.forEach(cit => {
      parts = parts.flatMap(part => {
        if (typeof part !== 'string') return [part];
        const segments = part.split(cit.match_text);
        const result = [];
        for (let k = 0; k < segments.length; k++) {
          result.push(segments[k]);
          if (k < segments.length - 1) {
            result.push(
              <span key={`cit-${cit.match_text}-${k}`} onClick={() => onCitationClick(cit)}
                style={{
                  color: '#000',
                  background: '#F0F0F0',
                  padding: '1px 4px', borderRadius: 3, cursor: 'pointer',
                  fontWeight: 600, fontSize: 13,
                }}
              >{cit.match_text}</span>
            );
          }
        }
        return result;
      });
    });
  }

  parts = parts.flatMap(part => {
    if (typeof part !== 'string') return [part];
    const tokens = part.split(/(\*\*[^*]+\*\*|__[^_]+__|`[^`]+`|\*[^*]+\*|\[Source:[^\]]+\]|\[MongoDB[^\]]+\]|\[IndianKanoon[^\]]+\]|\[From training[^\]]*\]|\[verify independently\])/g);
    return tokens.map((token, j) => {
      if (!token) return null;
      if ((token.startsWith('**') && token.endsWith('**')) || (token.startsWith('__') && token.endsWith('__')))
        return <strong key={j} style={{ fontWeight: 700, color: '#0A0A0A' }}>{token.slice(2, -2)}</strong>;
      if (token.startsWith('*') && token.endsWith('*') && !token.startsWith('**'))
        return <em key={j} style={{ color: '#374151' }}>{token.slice(1, -1)}</em>;
      if (token.startsWith('`') && token.endsWith('`'))
        return <code key={j} style={{ fontSize: 12, background: '#F3F4F6', padding: '1px 5px', borderRadius: 3, fontFamily: 'monospace', color: '#1A1A1A' }}>{token.slice(1, -1)}</code>;
      if (token === '[verify independently]' || token.startsWith('[From training'))
        return <span key={j} style={{ fontSize: 10, color: '#999', background: '#F5F5F5', padding: '1px 5px', borderRadius: 3, fontFamily: 'monospace' }}>{token}</span>;
      if (token.startsWith('[Source:') || token.startsWith('[MongoDB') || token.startsWith('[IndianKanoon'))
        return <span key={j} style={{ fontSize: 10, color: '#000', background: '#F5F5F5', padding: '1px 5px', borderRadius: 3, fontFamily: 'monospace' }}>{token}</span>;
      return token;
    });
  });

  return parts;
}

function renderTable(tableLines, keyBase) {
  if (tableLines.length < 2) return null;
  const parseRow = line => line.split('|').filter((_, i, arr) => i > 0 && i < arr.length - 1).map(c => c.trim());
  const headers = parseRow(tableLines[0]);
  const rows = tableLines.slice(2).map(parseRow);

  return (
    <div key={keyBase} style={{ overflowX: 'auto', margin: '14px 0', border: '1px solid #EDEDED', borderRadius: 8 }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr style={{ background: '#FAFAFA', borderBottom: '1px solid #EDEDED' }}>
            {headers.map((h, hi) => (
              <th key={hi} style={{ padding: '10px 14px', textAlign: 'left', fontWeight: 600, fontSize: 11.5, color: '#555', letterSpacing: '0.01em' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, ri) => (
            <tr key={ri} style={{ borderBottom: ri < rows.length - 1 ? '1px solid #F2F2F2' : 'none' }}>
              {row.map((cell, ci) => (
                <td key={ci} style={{ padding: '10px 14px', color: '#1A1A1A', fontWeight: ci === 0 ? 500 : 400, lineHeight: 1.5 }}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function detectSmartActions(text) {
  if (!text) return [];
  const actions = [];

  if (/\bscn\b|show cause notice|section 7[34]|drc-01/i.test(text))
    actions.push({ label: 'Draft SCN reply', icon: FileWarning, prompt: 'Draft a complete, filing-ready SCN reply based on the above analysis. Include cause title, factual background, legal submissions point-by-point, and prayer clause.' });
  if (/\bbail\b|section 43[89]|section 483|section 439/i.test(text))
    actions.push({ label: 'Draft bail application', icon: Gavel, prompt: 'Draft a complete bail application based on the above analysis. Include court header, case details, grounds for bail, undertakings, and prayer.' });
  if (/\btds\b|section 194|deduct.*tax at source/i.test(text))
    actions.push({ label: 'TDS computation table', icon: Table2, prompt: 'Generate a complete TDS computation table. Columns: Payment Type | Section | Rate | Threshold | Amount | TDS Amount. Include totals.' });
  if (/\bnotice\b.*\b(reply|response|challenge)\b|\breply to notice/i.test(text))
    actions.push({ label: 'Draft notice reply', icon: FileText, prompt: 'Draft a complete formal reply to the notice based on the above analysis.' });
  if (/\bpenalty\b.*\blate\b|\blate fee\b|\binterest.*delay/i.test(text))
    actions.push({ label: 'Penalty computation', icon: Table2, prompt: 'Generate a penalty computation sheet. Columns: Filing Type | Due Date | Actual Date | Days Late | Late Fee | Interest | Total.' });
  if (/\bappeal\b|first appellate|commissioner.*appeals|itat/i.test(text))
    actions.push({ label: 'Draft appeal memo', icon: FileText, prompt: 'Draft a complete appeal memorandum based on the above analysis.' });

  return actions.slice(0, 3);
}

export default function ResponseCard({ responseText, sections, sources, modelUsed, citations, internalStrategy, onExport, onDraft, onSmartAction }) {
  const [showReasoning, setShowReasoning] = useState(false);
  const [copied, setCopied] = useState(false);
  const [activeCitation, setActiveCitation] = useState(null);
  const [showExport, setShowExport] = useState(false);

  let fullText = responseText;
  if (!fullText && sections && sections.length > 0) {
    if (typeof sections[0] === 'object' && sections[0].content) {
      fullText = sections.map(s => s.content).join('\n\n');
    }
  }

  const riskData = useMemo(() => parseRiskAnalysis(fullText), [fullText]);
  const displayText = useMemo(() => stripRiskAnalysis(fullText), [fullText]);

  if (!fullText) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(fullText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const smartActions = detectSmartActions(fullText);

  return (
    <div style={{ position: 'relative' }}>
      {/* Response content — no border card, just clean text */}
      <div style={{ padding: '4px 0' }}>
        {/* Reasoning toggle */}
        {internalStrategy && (
          <div style={{ marginBottom: 14 }}>
            <button onClick={() => setShowReasoning(!showReasoning)}
              style={{
                display: 'flex', alignItems: 'center', gap: 6,
                padding: '4px 12px',
                background: showReasoning ? 'rgba(10,10,10,0.05)' : '#FAFAFA',
                border: `1px solid ${showReasoning ? 'rgba(10,10,10,0.12)' : '#EBEBEB'}`,
                borderRadius: 100, cursor: 'pointer',
                fontFamily: "'Inter', sans-serif",
                fontSize: 11.5, fontWeight: 600,
                color: showReasoning ? '#0A0A0A' : '#AAAAAA',
                transition: 'all 0.2s',
              }}
            >
              {showReasoning ? <EyeOff style={{ width: 10, height: 10 }} /> : <Eye style={{ width: 10, height: 10 }} />}
              {showReasoning ? 'Hide reasoning' : 'Show reasoning'}
            </button>
            {showReasoning && (
              <div style={{
                marginTop: 10, padding: '14px 16px',
                background: 'rgba(10,10,10,0.02)',
                border: '1px solid rgba(10,10,10,0.08)',
                borderRadius: 14, fontSize: 12, color: '#666',
                backdropFilter: 'blur(8px)', WebkitBackdropFilter: 'blur(8px)',
                fontFamily: "'IBM Plex Mono', monospace",
                lineHeight: 1.65, whiteSpace: 'pre-wrap',
                maxHeight: 240, overflowY: 'auto',
              }}>
                {internalStrategy}
              </div>
            )}
          </div>
        )}

        {/* Main content */}
        {renderMarkdownContent(displayText, citations || (sections && sections[0]?.citations), setActiveCitation)}

        {riskData && <RiskExposureCard risk={riskData} />}
      </div>

      {activeCitation && (
        <CitationPanel citation={activeCitation} onClose={() => setActiveCitation(null)} />
      )}

      {/* Action bar — premium */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 5, marginTop: 18, paddingTop: 14,
        borderTop: '1px solid #F5F5F5', flexWrap: 'wrap',
      }}>

        {/* Copy */}
        <button onClick={handleCopy}
          style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: 12, fontWeight: 500,
            padding: '5px 12px', background: copied ? '#0A0A0A' : '#FAFAFA',
            border: `1px solid ${copied ? '#0A0A0A' : '#EBEBEB'}`, borderRadius: 100, cursor: 'pointer',
            color: copied ? '#fff' : '#AAAAAA',
            display: 'flex', alignItems: 'center', gap: 5,
            transition: 'all 0.2s cubic-bezier(0.16,1,0.3,1)',
          }}
          onMouseEnter={e => { if (!copied) { e.currentTarget.style.borderColor = '#CCC'; e.currentTarget.style.color = '#555'; } }}
          onMouseLeave={e => { if (!copied) { e.currentTarget.style.borderColor = '#EBEBEB'; e.currentTarget.style.color = '#AAAAAA'; } }}
        >
          {copied ? <Check style={{ width: 10, height: 10 }} /> : <Copy style={{ width: 10, height: 10 }} />}
          {copied ? 'Copied!' : 'Copy'}
        </button>

        {/* Export dropdown */}
        {onExport && (
          <div style={{ position: 'relative' }}>
            <button onClick={() => setShowExport(!showExport)}
              style={{
                fontFamily: "'Inter', sans-serif",
                fontSize: 12, fontWeight: 500,
                padding: '5px 12px', background: '#FAFAFA',
                border: '1px solid #EBEBEB', borderRadius: 100, cursor: 'pointer',
                color: '#AAAAAA', display: 'flex', alignItems: 'center', gap: 5,
                transition: 'all 0.15s',
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = '#CCC'; e.currentTarget.style.color = '#555'; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = '#EBEBEB'; e.currentTarget.style.color = '#AAAAAA'; }}
            >
              <FileDown style={{ width: 10, height: 10 }} />
              Export
              <ChevronDown style={{ width: 9, height: 9 }} />
            </button>
            {showExport && (
              <div style={{
                position: 'absolute', bottom: 'calc(100% + 6px)', left: 0,
                background: 'rgba(255,255,255,0.95)',
                backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)',
                border: '1px solid #EBEBEB', borderRadius: 12,
                boxShadow: '0 8px 24px rgba(0,0,0,0.08)', zIndex: 20, padding: 4,
                minWidth: 110, animation: 'slideUp 0.14s cubic-bezier(0.16,1,0.3,1)',
              }}>
                {[
                  { fmt: 'docx', icon: FileText, label: 'Word (.docx)' },
                  { fmt: 'xlsx', icon: Table2, label: 'Excel (.xlsx)' },
                  { fmt: 'pdf', icon: FileDown, label: 'PDF (.pdf)' },
                ].map(({ fmt, icon: Ic, label }) => (
                  <button key={fmt} onClick={() => { onExport(fmt); setShowExport(false); }}
                    style={{
                      width: '100%', textAlign: 'left', padding: '7px 12px',
                      fontFamily: "'Inter', sans-serif",
                      fontSize: 12.5, fontWeight: 500, color: '#444', background: 'none', border: 'none',
                      cursor: 'pointer', borderRadius: 8, transition: 'background 0.1s',
                      display: 'flex', alignItems: 'center', gap: 8,
                    }}
                    onMouseEnter={e => e.currentTarget.style.background = '#F5F5F5'}
                    onMouseLeave={e => e.currentTarget.style.background = 'none'}
                  >
                    <Ic style={{ width: 12, height: 12, color: '#AAAAAA' }} /> {label}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Smart actions — accent */}
        {smartActions.map((action, idx) => (
          <button key={idx}
            onClick={() => onSmartAction ? onSmartAction(action.prompt) : onDraft?.()}
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: 12, fontWeight: 600,
              padding: '5px 12px',
              background: 'rgba(10,10,10,0.05)',
              border: '1px solid rgba(10,10,10,0.12)', borderRadius: 100, cursor: 'pointer',
              color: '#333', display: 'flex', alignItems: 'center', gap: 5,
              transition: 'all 0.2s cubic-bezier(0.16,1,0.3,1)',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.background = '#0A0A0A';
              e.currentTarget.style.borderColor = '#0A0A0A';
              e.currentTarget.style.color = '#fff';
              e.currentTarget.style.transform = 'translateY(-1px)';
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = 'rgba(10,10,10,0.05)';
              e.currentTarget.style.borderColor = 'rgba(10,10,10,0.12)';
              e.currentTarget.style.color = '#333';
              e.currentTarget.style.transform = 'translateY(0)';
            }}
          >
            <action.icon style={{ width: 10, height: 10 }} /> {action.label}
          </button>
        ))}

        {onDraft && (
          <button onClick={onDraft}
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: 12, fontWeight: 500,
              padding: '5px 12px', background: '#FAFAFA',
              border: '1px solid #EBEBEB', borderRadius: 100, cursor: 'pointer',
              color: '#AAAAAA', display: 'flex', alignItems: 'center', gap: 5,
              transition: 'all 0.15s',
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = '#CCC'; e.currentTarget.style.color = '#555'; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = '#EBEBEB'; e.currentTarget.style.color = '#AAAAAA'; }}
          >
            <Edit3 style={{ width: 10, height: 10 }} /> Draft
          </button>
        )}
      </div>
    </div>
  );
}
