import React, { useState, useMemo } from 'react';
import { FileDown, Edit3, Eye, EyeOff, Scale, Copy, Check, AlertTriangle, FileText, Table2, Gavel, FileWarning, ChevronDown } from 'lucide-react';
import CitationPanel from './CitationPanel';
import RiskExposureCard, { parseRiskAnalysis, stripRiskAnalysis } from './RiskExposureCard';

/**
 * Markdown renderer for Associate AI responses.
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
          background: '#1A1A1A', color: '#E2E8F0', padding: '14px 18px',
          borderRadius: 12, fontSize: 13, lineHeight: 1.7, overflowX: 'auto',
          fontFamily: "'Inter', sans-serif", margin: '10px 0',
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
        <h4 key={i} style={{ fontFamily: "'Plus Jakarta Sans', 'Inter', sans-serif", fontSize: 15, fontWeight: 700, color: '#0A0A0A', marginTop: 24, marginBottom: 8, paddingBottom: 6, borderBottom: '1px solid #F0F0F0', letterSpacing: '-0.01em' }}>
          {renderInline(trimmed.slice(4), citations, onCitationClick)}
        </h4>
      );
      i++; continue;
    }
    if (trimmed.startsWith('## ')) {
      elements.push(
        <h3 key={i} style={{ fontFamily: "'Plus Jakarta Sans', 'Inter', sans-serif", fontSize: 17, fontWeight: 700, color: '#0A0A0A', marginTop: 28, marginBottom: 8, letterSpacing: '-0.02em' }}>
          {renderInline(trimmed.slice(3), citations, onCitationClick)}
        </h3>
      );
      i++; continue;
    }
    if (trimmed.startsWith('# ')) {
      elements.push(
        <h2 key={i} style={{ fontFamily: "'Plus Jakarta Sans', 'Inter', sans-serif", fontSize: 20, fontWeight: 700, color: '#0A0A0A', marginTop: 32, marginBottom: 10, letterSpacing: '-0.03em' }}>
          {renderInline(trimmed.slice(2), citations, onCitationClick)}
        </h2>
      );
      i++; continue;
    }

    // Blockquote
    if (trimmed.startsWith('> ')) {
      const quoteLines = [];
      while (i < lines.length && lines[i].trim().startsWith('> ')) { quoteLines.push(lines[i].trim().slice(2)); i++; }
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

function renderInline(text, citations, onCitationClick) {
  if (!text) return null;

  let parts = [text];
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
    <div key={keyBase} style={{ overflowX: 'auto', margin: '12px 0' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #E5E5E5' }}>
            {headers.map((h, hi) => (
              <th key={hi} style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, fontSize: 12, color: '#4B5563' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, ri) => (
            <tr key={ri} style={{ borderBottom: '1px solid #F0F0F0' }}>
              {row.map((cell, ci) => (
                <td key={ci} style={{ padding: '7px 12px', color: '#1A1A1A', fontWeight: ci === 0 ? 500 : 400 }}>{cell}</td>
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
          <div style={{ marginBottom: 12 }}>
            <button onClick={() => setShowReasoning(!showReasoning)}
              style={{
                display: 'flex', alignItems: 'center', gap: 5,
                padding: '4px 10px', background: '#F5F5F5', border: '1px solid #EBEBEB',
                borderRadius: 100, cursor: 'pointer', fontSize: 12, color: '#999',
              }}
            >
              {showReasoning ? <EyeOff style={{ width: 11, height: 11 }} /> : <Eye style={{ width: 11, height: 11 }} />}
              {showReasoning ? 'Hide reasoning' : 'Show reasoning'}
            </button>
            {showReasoning && (
              <div style={{
                marginTop: 8, padding: '12px 14px', background: 'rgba(250,250,250,0.8)', border: '1px solid #F0F0F0',
                borderRadius: 14, fontSize: 12, color: '#666',
                backdropFilter: 'blur(8px)', WebkitBackdropFilter: 'blur(8px)',
                fontFamily: 'monospace', lineHeight: 1.6, whiteSpace: 'pre-wrap',
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

      {/* Action bar — compact, clean */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 4, marginTop: 16, paddingTop: 12,
        borderTop: '1px solid #F0F0F0', flexWrap: 'wrap',
      }}>
        {/* Copy */}
        <button onClick={handleCopy}
          style={{
            fontSize: 12, padding: '5px 10px', background: 'none',
            border: '1px solid #EBEBEB', borderRadius: 100, cursor: 'pointer',
            color: copied ? '#000' : '#999', display: 'flex', alignItems: 'center', gap: 4,
            transition: 'all 0.15s',
          }}
          onMouseEnter={e => { if (!copied) e.currentTarget.style.color = '#666'; }}
          onMouseLeave={e => { if (!copied) e.currentTarget.style.color = '#999'; }}
        >
          {copied ? <Check style={{ width: 11, height: 11 }} /> : <Copy style={{ width: 11, height: 11 }} />}
          {copied ? 'Copied' : 'Copy'}
        </button>

        {/* Export dropdown */}
        {onExport && (
          <div style={{ position: 'relative' }}>
            <button onClick={() => setShowExport(!showExport)}
              style={{
                fontSize: 12, padding: '5px 10px', background: 'none',
                border: '1px solid #EBEBEB', borderRadius: 100, cursor: 'pointer',
                color: '#999', display: 'flex', alignItems: 'center', gap: 4,
                transition: 'all 0.15s',
              }}
              onMouseEnter={e => e.currentTarget.style.color = '#666'}
              onMouseLeave={e => e.currentTarget.style.color = '#999'}
            >
              <FileDown style={{ width: 11, height: 11 }} />
              Export
              <ChevronDown style={{ width: 10, height: 10 }} />
            </button>
            {showExport && (
              <div style={{
                position: 'absolute', bottom: '110%', left: 0,
                background: 'rgba(255,255,255,0.92)', backdropFilter: 'blur(12px)', WebkitBackdropFilter: 'blur(12px)',
                border: '1px solid #E5E5E5', borderRadius: 12,
                boxShadow: '0 4px 12px rgba(0,0,0,0.06)', zIndex: 20, padding: 2,
                minWidth: 100,
              }}>
                {['docx', 'xlsx', 'pdf'].map(fmt => (
                  <button key={fmt} onClick={() => { onExport(fmt); setShowExport(false); }}
                    style={{
                      width: '100%', textAlign: 'left', padding: '6px 12px',
                      fontSize: 12, color: '#4B5563', background: 'none', border: 'none',
                      cursor: 'pointer', borderRadius: 4, transition: 'background 0.1s',
                    }}
                    onMouseEnter={e => e.currentTarget.style.background = '#F5F5F5'}
                    onMouseLeave={e => e.currentTarget.style.background = 'none'}
                  >
                    {fmt.toUpperCase()}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Smart actions */}
        {smartActions.map((action, idx) => (
          <button key={idx}
            onClick={() => onSmartAction ? onSmartAction(action.prompt) : onDraft?.()}
            style={{
              fontSize: 12, padding: '5px 10px', background: '#0A0A0A',
              border: 'none', borderRadius: 100, cursor: 'pointer',
              color: '#fff', display: 'flex', alignItems: 'center', gap: 4,
              transition: 'all 0.15s',
            }}
            onMouseEnter={e => e.currentTarget.style.background = '#333'}
            onMouseLeave={e => e.currentTarget.style.background = '#0A0A0A'}
          >
            <action.icon style={{ width: 11, height: 11 }} /> {action.label}
          </button>
        ))}

        {onDraft && (
          <button onClick={onDraft}
            style={{
              fontSize: 12, padding: '5px 10px', background: 'none',
              border: '1px solid #EBEBEB', borderRadius: 100, cursor: 'pointer',
              color: '#999', display: 'flex', alignItems: 'center', gap: 4,
              transition: 'all 0.15s',
            }}
            onMouseEnter={e => e.currentTarget.style.color = '#666'}
            onMouseLeave={e => e.currentTarget.style.color = '#999'}
          >
            <Edit3 style={{ width: 11, height: 11 }} /> Draft
          </button>
        )}
      </div>
    </div>
  );
}
