import React from 'react';
import { AlertTriangle, TrendingUp, Clock, ChevronRight, Shield, Zap } from 'lucide-react';

/**
 * Parses <risk_analysis> blocks from AI response text.
 * Returns null if no risk block found.
 */
export function parseRiskAnalysis(text) {
  if (!text) return null;
  const match = text.match(/<risk_analysis>([\s\S]*?)<\/risk_analysis>/);
  if (!match) return null;

  const block = match[1];
  const result = {};

  // Parse EXPOSURE line
  const exposure = block.match(/EXPOSURE:\s*(.+)/);
  if (exposure) {
    const amounts = exposure[1].match(/₹[\d,.\s]+(?:lakhs?|crores?|L|Cr)?/gi) || [];
    result.exposure = {
      raw: exposure[1].trim(),
      amounts: amounts.map(a => a.trim()),
    };
  }

  // Parse WIN_PROBABILITY
  const winProb = block.match(/WIN_PROBABILITY:\s*(.+)/);
  if (winProb) {
    const pctMatch = winProb[1].match(/(\d+)%/);
    result.winProbability = {
      raw: winProb[1].trim(),
      percent: pctMatch ? parseInt(pctMatch[1]) : null,
    };
  }

  // Parse STRATEGY lines
  const strategies = [];
  const stratRegex = /STRATEGY_[A-Z]:\s*(.+)/g;
  let stratMatch;
  while ((stratMatch = stratRegex.exec(block)) !== null) {
    const parts = stratMatch[1].split('|').map(s => s.trim());
    const name = parts[0]?.split('—')[0]?.trim() || parts[0]?.trim();
    const cost = parts.find(p => /cost/i.test(p))?.replace(/cost:\s*/i, '').trim();
    const timeline = parts.find(p => /timeline/i.test(p))?.replace(/timeline:\s*/i, '').trim();
    const success = parts.find(p => /success/i.test(p))?.replace(/success:\s*/i, '').trim();
    strategies.push({ name, cost, timeline, success, raw: stratMatch[1].trim() });
  }
  result.strategies = strategies;

  // Parse RECOMMENDED
  const recommended = block.match(/RECOMMENDED:\s*(.+)/);
  if (recommended) result.recommended = recommended[1].trim();

  // Parse DEADLINE
  const deadline = block.match(/DEADLINE:\s*(.+)/);
  if (deadline) {
    const daysMatch = deadline[1].match(/(\d+)\s*days?/);
    result.deadline = {
      raw: deadline[1].trim(),
      daysRemaining: daysMatch ? parseInt(daysMatch[1]) : null,
    };
  }

  // Parse CASCADE
  const cascade = block.match(/CASCADE:\s*(.+)/);
  if (cascade) {
    result.cascade = cascade[1].trim().split('→').map(s => s.trim()).filter(Boolean);
  }

  // Only return if we got meaningful data
  if (!result.exposure && !result.strategies?.length && !result.winProbability) return null;
  return result;
}

/**
 * Strips <risk_analysis> block from text for clean markdown rendering.
 */
export function stripRiskAnalysis(text) {
  if (!text) return text;
  return text.replace(/<risk_analysis>[\s\S]*?<\/risk_analysis>/g, '').trim();
}

/**
 * Visual Risk Intelligence Card — the core differentiator.
 */
export default function RiskExposureCard({ risk }) {
  if (!risk) return null;

  const urgencyColor = risk.deadline?.daysRemaining != null
    ? risk.deadline.daysRemaining <= 7 ? '#000'
    : risk.deadline.daysRemaining <= 30 ? '#000'
    : '#0A0A0A'
    : '#6B7280';

  const winColor = risk.winProbability?.percent != null
    ? risk.winProbability.percent >= 70 ? '#0A0A0A'
    : risk.winProbability.percent >= 40 ? '#000'
    : '#000'
    : '#6B7280';

  return (
    <div style={{
      margin: '20px 0 8px',
      borderRadius: 12,
      border: '1px solid #E2E8F0',
      overflow: 'hidden',
      background: '#FFFFFF',
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 20px',
        background: '#0A0A0A',
        display: 'flex', alignItems: 'center', gap: 8,
      }}>
        <Zap style={{ width: 14, height: 14, color: '#FBBF24' }} />
        <span style={{ fontSize: 11, fontWeight: 700, color: '#FFFFFF', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
          Risk Intelligence
        </span>
      </div>

      <div style={{ padding: '16px 20px' }}>
        {/* Exposure Row */}
        {risk.exposure && (
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 10, fontWeight: 600, color: '#6B7280', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 }}>
              Exposure Range
            </div>
            <div style={{ fontSize: 15, fontWeight: 600, color: '#0A0A0A', lineHeight: 1.5 }}>
              {risk.exposure.raw}
            </div>
          </div>
        )}

        {/* Win Probability + Deadline Row */}
        <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
          {risk.winProbability && (
            <div style={{
              flex: 1, padding: '12px 14px', borderRadius: 8,
              border: `1px solid ${winColor}20`, background: `${winColor}08`,
            }}>
              <div style={{ fontSize: 10, fontWeight: 600, color: '#6B7280', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4, display: 'flex', alignItems: 'center', gap: 4 }}>
                <TrendingUp style={{ width: 10, height: 10 }} /> Win Probability
              </div>
              {risk.winProbability.percent != null && (
                <div style={{ fontSize: 28, fontWeight: 800, color: winColor, fontFamily: "'Inter', sans-serif" }}>
                  {risk.winProbability.percent}%
                </div>
              )}
              <div style={{ fontSize: 11, color: '#4B5563', lineHeight: 1.4, marginTop: 2 }}>
                {risk.winProbability.raw.replace(/^\d+%\s*/, '')}
              </div>
            </div>
          )}

          {risk.deadline && (
            <div style={{
              flex: 1, padding: '12px 14px', borderRadius: 8,
              border: `1px solid ${urgencyColor}20`, background: `${urgencyColor}08`,
            }}>
              <div style={{ fontSize: 10, fontWeight: 600, color: '#6B7280', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4, display: 'flex', alignItems: 'center', gap: 4 }}>
                <Clock style={{ width: 10, height: 10 }} /> Next Deadline
              </div>
              {risk.deadline.daysRemaining != null && (
                <div style={{ fontSize: 28, fontWeight: 800, color: urgencyColor, fontFamily: "'Inter', sans-serif" }}>
                  {risk.deadline.daysRemaining}d
                </div>
              )}
              <div style={{ fontSize: 11, color: '#4B5563', lineHeight: 1.4, marginTop: 2 }}>
                {risk.deadline.raw.replace(/\d+\s*days?\s*/, '')}
              </div>
            </div>
          )}
        </div>

        {/* Strategy Comparison */}
        {risk.strategies?.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 10, fontWeight: 600, color: '#6B7280', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 4 }}>
              <Shield style={{ width: 10, height: 10 }} /> Strategy Comparison
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {risk.strategies.map((s, i) => {
                const isRecommended = risk.recommended?.toLowerCase().includes(s.name?.toLowerCase());
                return (
                  <div key={i} style={{
                    padding: '10px 14px', borderRadius: 8,
                    border: isRecommended ? '2px solid #0A0A0A' : '1px solid #E2E8F0',
                    background: isRecommended ? '#F8FAFC' : '#FFFFFF',
                    display: 'flex', alignItems: 'center', gap: 12,
                  }}>
                    {isRecommended && (
                      <span style={{
                        fontSize: 8, fontWeight: 800, color: '#fff', background: '#0A0A0A',
                        padding: '2px 6px', borderRadius: 3, textTransform: 'uppercase', letterSpacing: '0.1em',
                        flexShrink: 0,
                      }}>Best</span>
                    )}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 13, fontWeight: 600, color: '#0A0A0A' }}>{s.name}</div>
                      <div style={{ fontSize: 11, color: '#6B7280', display: 'flex', gap: 12, flexWrap: 'wrap', marginTop: 2 }}>
                        {s.cost && <span>Cost: <strong style={{ color: '#0A0A0A' }}>{s.cost}</strong></span>}
                        {s.timeline && <span>Timeline: <strong style={{ color: '#0A0A0A' }}>{s.timeline}</strong></span>}
                        {s.success && <span>Success: <strong style={{ color: '#0A0A0A' }}>{s.success}</strong></span>}
                      </div>
                    </div>
                    <ChevronRight style={{ width: 14, height: 14, color: '#94A3B8', flexShrink: 0 }} />
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Recommended */}
        {risk.recommended && (
          <div style={{
            padding: '10px 14px', borderRadius: 8,
            background: '#FAFAFA', border: '1px solid #E5E5E5',
            fontSize: 12, color: '#000', fontWeight: 500, lineHeight: 1.5,
            display: 'flex', alignItems: 'flex-start', gap: 8, marginBottom: 16,
          }}>
            <AlertTriangle style={{ width: 14, height: 14, flexShrink: 0, marginTop: 1 }} />
            <div><strong>Recommended:</strong> {risk.recommended}</div>
          </div>
        )}

        {/* Cascade */}
        {risk.cascade?.length > 0 && (
          <div>
            <div style={{ fontSize: 10, fontWeight: 600, color: '#6B7280', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 }}>
              Impact Cascade
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexWrap: 'wrap' }}>
              {risk.cascade.map((item, i) => (
                <React.Fragment key={i}>
                  <span style={{
                    fontSize: 11, fontWeight: 500, color: '#0A0A0A',
                    padding: '4px 8px', background: '#F3F4F6', borderRadius: 4,
                    whiteSpace: 'nowrap',
                  }}>{item}</span>
                  {i < risk.cascade.length - 1 && (
                    <ChevronRight style={{ width: 12, height: 12, color: '#D1D5DB', flexShrink: 0 }} />
                  )}
                </React.Fragment>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
