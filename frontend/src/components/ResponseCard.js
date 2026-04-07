import React, { useState, useMemo } from 'react';
import { FileDown, Edit3, Eye, EyeOff, Scale, Copy, Check, BookOpen, Shield, AlertTriangle } from 'lucide-react';
import CitationPanel from './CitationPanel';

/**
 * Premium Markdown-aware renderer for Associate AI responses.
 * Renders: headers, bold, italic, tables, blockquotes, lists,
 * numbered items, code blocks, horizontal rules, source tags,
 * and citation highlights.
 */
function renderMarkdownContent(content, citations, onCitationClick) {
  if (!content) return null;
  const lines = String(content).split('\n');
  const elements = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    // Empty line
    if (!trimmed) {
      elements.push(<div key={i} style={{ height: 10 }} />);
      i++;
      continue;
    }

    // Horizontal rule
    if (/^---+$/.test(trimmed) || /^\*\*\*+$/.test(trimmed)) {
      elements.push(
        <hr key={i} style={{ border: 'none', borderTop: '1px solid #E5E7EB', margin: '20px 0' }} />
      );
      i++;
      continue;
    }

    // Table detection (starts with |)
    if (trimmed.startsWith('|')) {
      const tableLines = [];
      while (i < lines.length && lines[i].trim().startsWith('|')) {
        tableLines.push(lines[i].trim());
        i++;
      }
      elements.push(renderTable(tableLines, elements.length));
      continue;
    }

    // Code block
    if (trimmed.startsWith('```')) {
      const codeLines = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith('```')) {
        codeLines.push(lines[i]);
        i++;
      }
      i++; // skip closing ```
      elements.push(
        <pre key={elements.length} style={{
          background: '#1A1A2E', color: '#E2E8F0', padding: '16px 20px',
          borderRadius: 10, fontSize: 13, lineHeight: 1.7, overflowX: 'auto',
          fontFamily: "'IBM Plex Mono', 'Fira Code', monospace",
          margin: '12px 0', border: '1px solid #2D2D44',
        }}>
          {codeLines.join('\n')}
        </pre>
      );
      continue;
    }

    // Headers — ####, ###, ##, and #
    if (trimmed.startsWith('#### ') || trimmed.startsWith('##### ')) {
      const text = trimmed.replace(/^#+\s/, '');
      elements.push(
        <h5 key={i} style={{
          fontSize: 14, fontWeight: 700, color: '#374151', marginTop: 20, marginBottom: 8,
          letterSpacing: '-0.01em', textTransform: 'uppercase'
        }}>
          {renderInline(text, citations, onCitationClick)}
        </h5>
      );
      i++;
      continue;
    }
    if (trimmed.startsWith('### ')) {
      elements.push(
        <h4 key={i} style={{
          fontSize: 15, fontWeight: 800, color: '#000000', marginTop: 28, marginBottom: 8,
          letterSpacing: '-0.02em', display: 'flex', alignItems: 'center', gap: 8,
          borderBottom: '1px solid #F3F4F6', paddingBottom: 8,
        }}>
          <span style={{ width: 3, height: 18, background: '#000', borderRadius: 2, flexShrink: 0 }} />
          {renderInline(trimmed.slice(4), citations, onCitationClick)}
        </h4>
      );
      i++;
      continue;
    }
    if (trimmed.startsWith('## ')) {
      elements.push(
        <h3 key={i} style={{
          fontSize: 17, fontWeight: 800, color: '#000000', marginTop: 32, marginBottom: 10,
          letterSpacing: '-0.03em', borderBottom: '2px solid #000', paddingBottom: 10,
        }}>
          {renderInline(trimmed.slice(3), citations, onCitationClick)}
        </h3>
      );
      i++;
      continue;
    }
    if (trimmed.startsWith('# ')) {
      elements.push(
        <h2 key={i} style={{
          fontSize: 20, fontWeight: 800, color: '#000000', marginTop: 36, marginBottom: 12,
          letterSpacing: '-0.03em',
        }}>
          {renderInline(trimmed.slice(2), citations, onCitationClick)}
        </h2>
      );
      i++;
      continue;
    }

    // Blockquote (>)
    if (trimmed.startsWith('> ')) {
      const quoteLines = [];
      while (i < lines.length && lines[i].trim().startsWith('> ')) {
        quoteLines.push(lines[i].trim().slice(2));
        i++;
      }
      elements.push(
        <blockquote key={elements.length} style={{
          borderLeft: '3px solid #000', paddingLeft: 16, margin: '12px 0',
          color: '#374151', fontStyle: 'italic', fontSize: 14, lineHeight: 1.8,
          background: '#FAFAFA', padding: '12px 16px', borderRadius: '0 8px 8px 0',
        }}>
          {quoteLines.map((ql, qi) => (
            <p key={qi} style={{ margin: '4px 0' }}>{renderInline(ql, citations, onCitationClick)}</p>
          ))}
        </blockquote>
      );
      continue;
    }

    // Warning/Risk callout
    if (trimmed.startsWith('⚠️') || trimmed.startsWith('**⚠️') || trimmed.includes('Risk Area') || trimmed.includes('WARNING') || trimmed.includes('CAUTION')) {
      elements.push(
        <div key={i} style={{
          background: '#FFFBEB', border: '1px solid #FDE68A', borderRadius: 8,
          padding: '10px 14px', margin: '10px 0', fontSize: 14, lineHeight: 1.7,
          display: 'flex', alignItems: 'flex-start', gap: 10,
        }}>
          <AlertTriangle style={{ width: 16, height: 16, color: '#D97706', flexShrink: 0, marginTop: 3 }} />
          <span>{renderInline(trimmed, citations, onCitationClick)}</span>
        </div>
      );
      i++;
      continue;
    }

    // Bullet points
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      elements.push(
        <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 10, margin: '4px 0', paddingLeft: 4 }}>
          <span style={{ color: '#000', fontSize: 6, marginTop: 10, flexShrink: 0 }}>●</span>
          <p style={{ fontSize: 15, lineHeight: 1.85, color: '#1A1A1A', margin: 0 }}>
            {renderInline(trimmed.replace(/^[-*]\s*/, ''), citations, onCitationClick)}
          </p>
        </div>
      );
      i++;
      continue;
    }

    // Sub-bullets (indented)
    if (line.startsWith('  - ') || line.startsWith('  * ') || line.startsWith('    - ')) {
      elements.push(
        <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 10, margin: '2px 0', paddingLeft: 28 }}>
          <span style={{ color: '#9CA3AF', fontSize: 5, marginTop: 10, flexShrink: 0 }}>○</span>
          <p style={{ fontSize: 14, lineHeight: 1.8, color: '#374151', margin: 0 }}>
            {renderInline(trimmed.replace(/^[-*]\s*/, ''), citations, onCitationClick)}
          </p>
        </div>
      );
      i++;
      continue;
    }

    // Numbered items
    if (/^\d+\.\s/.test(trimmed)) {
      const num = trimmed.match(/^(\d+)\./)[1];
      elements.push(
        <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 12, margin: '6px 0', paddingLeft: 4 }}>
          <span style={{
            fontSize: 13, fontWeight: 800, color: '#000000',
            fontFamily: "'IBM Plex Mono', monospace", marginTop: 3, flexShrink: 0,
            minWidth: 22, textAlign: 'right',
          }}>{num}.</span>
          <p style={{ fontSize: 15, lineHeight: 1.85, color: '#1A1A1A', margin: 0 }}>
            {renderInline(trimmed.replace(/^\d+\.\s*/, ''), citations, onCitationClick)}
          </p>
        </div>
      );
      i++;
      continue;
    }

    // Money highlight
    const isMoney = /₹[\d,]+/.test(trimmed);

    // Default paragraph
    elements.push(
      <p key={i} style={{
        fontSize: 15, lineHeight: 1.9, color: '#1A1A1A', margin: '3px 0',
        ...(isMoney ? {
          background: '#FFFBEB', borderLeft: '3px solid #D97706',
          paddingLeft: 14, borderRadius: '0 6px 6px 0', padding: '4px 10px 4px 14px',
        } : {}),
      }}>
        {renderInline(trimmed, citations, onCitationClick)}
      </p>
    );
    i++;
  }

  return elements;
}

/** Render inline markdown: **bold**, *italic*, `code`, source tags, citations */
function renderInline(text, citations, onCitationClick) {
  if (!text) return null;

  // First pass: citation replacement
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
              <span
                key={`cit-${cit.match_text}-${k}`}
                onClick={() => onCitationClick(cit)}
                style={{
                  color: cit.type === 'statute' ? '#166534' : '#1D4ED8',
                  background: cit.type === 'statute' ? '#DCFCE7' : '#DBEAFE',
                  padding: '1px 5px', borderRadius: 4, cursor: 'pointer',
                  fontWeight: 700, borderBottom: '1.5px dashed currentColor',
                  transition: 'all 0.2s', fontSize: 14,
                }}
                onMouseEnter={e => e.currentTarget.style.opacity = '0.7'}
                onMouseLeave={e => e.currentTarget.style.opacity = '1'}
              >
                {cit.match_text}
              </span>
            );
          }
        }
        return result;
      });
    });
  }

  // Second pass: inline markdown
  parts = parts.flatMap(part => {
    if (typeof part !== 'string') return [part];
    // Split on bold, italic, inline code, source tags, alert emojis
    const tokens = part.split(/(\*\*[^*]+\*\*|__[^_]+__|`[^`]+`|\*[^*]+\*|\[Source:[^\]]+\]|\[MongoDB[^\]]+\]|\[IndianKanoon[^\]]+\]|\[From training[^\]]*\]|\[verify independently\]|\[🚨[^\]]+\]|\[📌[^\]]+\])/g);
    return tokens.map((token, j) => {
      if (!token) return null;
      // Bold
      if ((token.startsWith('**') && token.endsWith('**')) || (token.startsWith('__') && token.endsWith('__'))) {
        return <strong key={j} style={{ fontWeight: 800, color: '#0A0A0A' }}>{token.slice(2, -2)}</strong>;
      }
      // Italic
      if (token.startsWith('*') && token.endsWith('*') && !token.startsWith('**')) {
        return <em key={j} style={{ fontStyle: 'italic', color: '#374151' }}>{token.slice(1, -1)}</em>;
      }
      // Inline code
      if (token.startsWith('`') && token.endsWith('`')) {
        return <code key={j} style={{
          fontSize: 13, background: '#F3F4F6', border: '1px solid #E5E7EB',
          padding: '1px 6px', borderRadius: 4, fontFamily: "'IBM Plex Mono', monospace",
          color: '#1A1A1A',
        }}>{token.slice(1, -1)}</code>;
      }
      // Alert tags
      if (token.startsWith('[🚨'))
        return <span key={j} style={{ fontSize: 13, color: '#DC2626', fontWeight: 700 }}>{token}</span>;
      if (token.startsWith('[📌'))
        return <span key={j} style={{ fontSize: 13, color: '#92400E', fontWeight: 600 }}>{token}</span>;
      // Verification tag
      if (token === '[verify independently]' || token.startsWith('[From training'))
        return <span key={j} style={{
          fontSize: 10.5, color: '#6B7280', background: '#FEF3C7', border: '1px solid #FDE68A',
          padding: '1px 6px', borderRadius: 3, fontFamily: "'IBM Plex Mono', monospace",
          fontWeight: 600, marginLeft: 2,
        }}>{token}</span>;
      // Source tags
      if (token.startsWith('[Source:') || token.startsWith('[MongoDB') || token.startsWith('[IndianKanoon'))
        return <span key={j} style={{
          fontSize: 10.5, color: '#166534', background: '#F0FDF4', border: '1px solid #BBF7D0',
          padding: '1px 6px', borderRadius: 3, marginLeft: 3,
          fontFamily: "'IBM Plex Mono', monospace", fontWeight: 600,
        }}>{token}</span>;
      return token;
    });
  });

  return parts;
}

/** Render a markdown table */
function renderTable(tableLines, keyBase) {
  if (tableLines.length < 2) return null;
  const parseRow = line => line.split('|').filter((_, i, arr) => i > 0 && i < arr.length - 1).map(c => c.trim());
  const headers = parseRow(tableLines[0]);
  // Skip separator row (index 1)
  const rows = tableLines.slice(2).map(parseRow);

  return (
    <div key={keyBase} style={{ overflowX: 'auto', margin: '16px 0' }}>
      <table style={{
        width: '100%', borderCollapse: 'collapse', fontSize: 13, lineHeight: 1.6,
        border: '1px solid #E5E7EB', borderRadius: 8, overflow: 'hidden',
      }}>
        <thead>
          <tr style={{ background: '#000', color: '#FFF' }}>
            {headers.map((h, hi) => (
              <th key={hi} style={{
                padding: '10px 14px', textAlign: 'left', fontWeight: 700,
                fontSize: 12, letterSpacing: '0.03em', textTransform: 'uppercase',
                borderRight: hi < headers.length - 1 ? '1px solid #333' : 'none',
              }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, ri) => (
            <tr key={ri} style={{ background: ri % 2 === 0 ? '#FFFFFF' : '#FAFAFA', borderBottom: '1px solid #F3F4F6' }}>
              {row.map((cell, ci) => (
                <td key={ci} style={{
                  padding: '9px 14px', color: '#1A1A1A', fontWeight: ci === 0 ? 600 : 400,
                  borderRight: ci < row.length - 1 ? '1px solid #F3F4F6' : 'none',
                }}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}


export default function ResponseCard({ responseText, sections, sources, modelUsed, citations, internalStrategy, onExport, onDraft }) {
  const [showReasoning, setShowReasoning] = useState(false);
  const [copied, setCopied] = useState(false);
  const [activeCitation, setActiveCitation] = useState(null);

  let fullText = responseText;
  if (!fullText && sections && sections.length > 0) {
    if (typeof sections[0] === 'object' && sections[0].content) {
      fullText = sections.map(s => s.content).join('\n\n');
    }
  }
  if (!fullText) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(fullText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const engineCount = modelUsed ? (modelUsed.match(/\d+/) || ['4'])[0] : '4';

  return (
    <div data-testid="response-card" style={{
      background: '#FFFFFF',
      border: '1px solid #E5E7EB',
      borderRadius: 16,
      overflow: 'hidden',
      boxShadow: '0 4px 30px rgba(0,0,0,0.04)',
    }}>
      {/* Premium Header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '14px 24px',
        borderBottom: '1px solid #F3F4F6',
        background: '#FAFAFA',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 22, height: 22, background: '#000000', borderRadius: 6,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <Scale style={{ width: 11, height: 11, color: '#FFFFFF' }} />
          </div>
          <span style={{
            fontSize: 12, fontWeight: 800, color: '#000000',
            letterSpacing: '0.05em', textTransform: 'uppercase',
          }}>
            Associate
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <button onClick={handleCopy}
            style={{
              fontSize: 11, fontWeight: 600, padding: '5px 12px',
              background: copied ? '#F0FDF4' : 'none',
              border: `1px solid ${copied ? '#BBF7D0' : '#E5E7EB'}`,
              borderRadius: 6,
              color: copied ? '#166534' : '#6B7280', cursor: 'pointer',
              transition: 'all 0.15s',
              display: 'flex', alignItems: 'center', gap: 4,
            }}
            data-testid="copy-response-btn">
            {copied ? <Check style={{ width: 11, height: 11 }} /> : <Copy style={{ width: 11, height: 11 }} />}
            {copied ? 'Copied' : 'Copy'}
          </button>
        </div>
      </div>

      {/* Internal Reasoning Toggle */}
      {internalStrategy && (
        <div style={{ borderBottom: '1px solid #F3F4F6' }}>
          <button onClick={() => setShowReasoning(!showReasoning)}
            style={{
              width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '8px 24px', background: 'none', border: 'none', cursor: 'pointer',
              transition: 'background 0.15s',
            }}
            onMouseEnter={e => e.currentTarget.style.background = '#FAFAFA'}
            onMouseLeave={e => e.currentTarget.style.background = 'none'}
            data-testid="show-reasoning-btn">
            <span style={{
              fontSize: 11, fontWeight: 600, letterSpacing: '0.04em',
              textTransform: 'uppercase', display: 'flex', alignItems: 'center',
              gap: 6, color: '#9CA3AF',
            }}>
              {showReasoning ?
                <EyeOff style={{ width: 11, height: 11 }} /> :
                <Eye style={{ width: 11, height: 11 }} />
              }
              <BookOpen style={{ width: 11, height: 11 }} />
              Internal Strategy Chain
            </span>
          </button>
          {showReasoning && (
            <div style={{
              padding: '14px 24px', background: '#FAFAFA', borderTop: '1px solid #F3F4F6',
              fontSize: 12.5, color: '#4B5563',
              fontFamily: "'IBM Plex Mono', monospace",
              lineHeight: 1.7, whiteSpace: 'pre-wrap', maxHeight: 300, overflowY: 'auto',
            }}>
              {internalStrategy}
            </div>
          )}
        </div>
      )}

      {/* The Premier Content Area */}
      <div style={{ padding: '28px 32px 32px' }}>
        {renderMarkdownContent(fullText, citations || (sections && sections[0]?.citations), setActiveCitation)}
      </div>

      {activeCitation && (
        <CitationPanel citation={activeCitation} onClose={() => setActiveCitation(null)} />
      )}

      {/* Premium footer */}
      <div style={{
        padding: '12px 24px', borderTop: '1px solid #F3F4F6', background: '#FAFAFA',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8,
      }}>
        {/* Source indicators */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
          {sources?.statutes_referenced && (
            <span style={{ fontSize: 10.5, fontWeight: 700, padding: '3px 10px', background: '#F0FDF4', border: '1px solid #BBF7D0', borderRadius: 4, color: '#166534', display: 'flex', alignItems: 'center', gap: 4 }}>
              <Shield style={{ width: 10, height: 10 }} /> Statute DB Verified
            </span>
          )}
          {sources?.indiankanoon?.length > 0 && (
            <span style={{ fontSize: 10.5, fontWeight: 700, padding: '3px 10px', background: '#EFF6FF', border: '1px solid #BFDBFE', borderRadius: 4, color: '#1D4ED8', display: 'flex', alignItems: 'center', gap: 4 }}>
              <BookOpen style={{ width: 10, height: 10 }} /> IndianKanoon ({sources.indiankanoon.length})
            </span>
          )}
          <span style={{ fontSize: 10.5, fontWeight: 700, padding: '3px 10px', background: '#FFFBEB', border: '1px solid #FDE68A', borderRadius: 4, color: '#92400E', display: 'flex', alignItems: 'center', gap: 4 }}>
            <Shield style={{ width: 10, height: 10 }} /> Citation Guard
          </span>
        </div>

        {/* Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
          {onExport && ['docx', 'pdf'].map(fmt => (
            <button key={fmt} onClick={() => onExport(fmt)}
              style={{
                fontSize: 11, fontWeight: 700, padding: '5px 12px',
                background: '#fff', border: '1px solid #E5E7EB', borderRadius: 6,
                color: '#6B7280', cursor: 'pointer', transition: 'all 0.15s',
                display: 'flex', alignItems: 'center', gap: 4,
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = '#000'; e.currentTarget.style.color = '#000'; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = '#E5E7EB'; e.currentTarget.style.color = '#6B7280'; }}
              data-testid={`export-${fmt}-btn`}>
              <FileDown style={{ width: 11, height: 11 }} /> {fmt.toUpperCase()}
            </button>
          ))}
          {onDraft && (
            <button onClick={onDraft}
              style={{
                fontSize: 11, fontWeight: 700, padding: '5px 14px',
                background: '#000', border: '1px solid #000', borderRadius: 6,
                color: '#fff', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4,
              }}
              data-testid="draft-this-btn">
              <Edit3 style={{ width: 11, height: 11 }} /> Draft →
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
