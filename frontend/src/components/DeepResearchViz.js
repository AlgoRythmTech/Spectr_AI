import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Globe, Brain, CheckCircle2, Loader2, ExternalLink, FileSearch } from 'lucide-react';

/**
 * Deep Research live visualization.
 * Shows phase-by-phase progress with source citations.
 *
 * Props:
 *   phase: 'searching' | 'hitting-sites' | 'extracting' | 'synthesizing' | 'done' | 'idle'
 *   sitesHit: number
 *   pageCount: number
 *   sourcesCount: number
 *   sources: Array<{ title, url, snippet }>
 *   message?: string (custom status text)
 */
export function DeepResearchViz({
  phase = 'idle',
  sitesHit = 0,
  pageCount = 0,
  sourcesCount = 0,
  sources = [],
  message,
}) {
  if (phase === 'idle') return null;

  const phases = [
    { key: 'searching',     label: 'Searching IndianKanoon',       icon: Search, duration: '~5s' },
    { key: 'hitting-sites', label: 'Hitting legal databases',      icon: Globe,  duration: '~30s' },
    { key: 'extracting',    label: 'Extracting findings',          icon: FileSearch, duration: '~10s' },
    { key: 'synthesizing',  label: 'Synthesizing with Claude Opus 4.7', icon: Brain, duration: '~15s' },
    { key: 'done',          label: 'Complete',                     icon: CheckCircle2, duration: '' },
  ];

  const activeIdx = phases.findIndex(p => p.key === phase);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
      style={{
        borderRadius: 12, background: '#fff',
        border: '1px solid rgba(100,68,245,0.15)',
        boxShadow: '0 4px 16px rgba(100,68,245,0.06)',
        overflow: 'hidden',
        fontFamily: "'Inter', sans-serif",
      }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 10,
        background: 'linear-gradient(90deg, rgba(100,68,245,0.04), rgba(24,204,252,0.04))',
        borderBottom: '1px solid rgba(100,68,245,0.1)',
      }}>
        <div style={{ width: 28, height: 28, borderRadius: 7, background: 'rgba(100,68,245,0.1)', border: '1px solid rgba(100,68,245,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Brain style={{ width: 14, height: 14, color: 'rgba(100,68,245,0.8)' }} />
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: '#0A0A0A', letterSpacing: '-.01em' }}>Deep Research</div>
          <div style={{ fontSize: 11, color: '#888', marginTop: 1 }}>
            {phase === 'done'
              ? `Found ${sourcesCount} sources across ${sitesHit} sites (${pageCount} pages)`
              : message || phases[activeIdx]?.label}
          </div>
        </div>
        {phase !== 'done' && (
          <Loader2 style={{ width: 14, height: 14, color: 'rgba(100,68,245,0.6)', animation: 'spin 0.8s linear infinite' }} />
        )}
      </div>

      {/* Phase progress */}
      <div style={{ padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 8 }}>
        {phases.slice(0, -1).map((p, i) => {
          const active = i === activeIdx;
          const done = i < activeIdx || phase === 'done';
          const Icon = p.icon;
          return (
            <motion.div key={p.key}
              animate={{ opacity: done || active ? 1 : 0.35 }}
              style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{
                width: 22, height: 22, borderRadius: 6,
                background: done ? 'rgba(34,197,94,0.1)' : active ? 'rgba(100,68,245,0.1)' : '#F5F5F5',
                border: `1px solid ${done ? 'rgba(34,197,94,0.25)' : active ? 'rgba(100,68,245,0.25)' : '#EBEBEB'}`,
                display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                transition: 'all 0.3s',
              }}>
                {done ? (
                  <CheckCircle2 style={{ width: 11, height: 11, color: '#22C55E' }} />
                ) : active ? (
                  <Loader2 style={{ width: 11, height: 11, color: 'rgba(100,68,245,0.8)', animation: 'spin 0.8s linear infinite' }} />
                ) : (
                  <Icon style={{ width: 10, height: 10, color: '#AAA' }} />
                )}
              </div>
              <span style={{ flex: 1, fontSize: 12.5, fontWeight: active ? 600 : 500, color: done ? '#22C55E' : active ? '#0A0A0A' : '#888' }}>
                {p.label}
              </span>
              {p.duration && (
                <span style={{ fontSize: 10.5, color: '#BBB', fontFamily: "'JetBrains Mono', monospace" }}>{p.duration}</span>
              )}
            </motion.div>
          );
        })}
      </div>

      {/* Sources — shown when done */}
      <AnimatePresence>
        {phase === 'done' && sources.length > 0 && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            style={{ borderTop: '1px solid #F5F5F5', overflow: 'hidden' }}>
            <div style={{ padding: '12px 16px' }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: '#AAA', letterSpacing: '.06em', textTransform: 'uppercase', marginBottom: 8 }}>
                Sources ({sources.length})
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {sources.slice(0, 12).map((s, i) => (
                  <motion.a
                    key={i}
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: i * 0.03 }}
                    href={s.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    title={s.snippet}
                    style={{
                      display: 'inline-flex', alignItems: 'center', gap: 5,
                      padding: '5px 10px', background: '#FAFAFA',
                      border: '1px solid #EBEBEB', borderRadius: 6,
                      fontSize: 11, fontWeight: 500, color: '#555',
                      textDecoration: 'none', maxWidth: 220,
                      transition: 'all 0.2s',
                    }}
                    onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(100,68,245,0.35)'; e.currentTarget.style.color = '#0A0A0A'; }}
                    onMouseLeave={e => { e.currentTarget.style.borderColor = '#EBEBEB'; e.currentTarget.style.color = '#555'; }}>
                    <ExternalLink style={{ width: 9, height: 9, flexShrink: 0, opacity: 0.5 }} />
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {s.title || (s.url || '').replace(/^https?:\/\//, '').split('/')[0]}
                    </span>
                  </motion.a>
                ))}
                {sources.length > 12 && (
                  <span style={{ fontSize: 11, color: '#888', padding: '5px 8px' }}>+{sources.length - 12} more</span>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
