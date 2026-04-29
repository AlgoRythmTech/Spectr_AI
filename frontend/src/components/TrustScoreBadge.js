import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Shield, ShieldCheck, ShieldAlert, X, Check, AlertTriangle } from 'lucide-react';

/**
 * Trust score badge — shown near AI response headers.
 * Click to expand verification report.
 *
 * Props:
 *   trustScore: number 0-100
 *   stats: { verified_count, unverified_count, total_citations, ... }
 *   verificationReport: string (markdown)
 *   notes: string[]
 */
export function TrustScoreBadge({ trustScore, stats, verificationReport, notes }) {
  const [open, setOpen] = useState(false);

  if (typeof trustScore !== 'number') return null;

  // Color based on score
  const color = trustScore >= 80 ? '#22C55E' : trustScore >= 50 ? '#F59E0B' : '#EF4444';
  const Icon = trustScore >= 80 ? ShieldCheck : trustScore >= 50 ? Shield : ShieldAlert;
  const label = trustScore >= 80 ? 'Verified' : trustScore >= 50 ? 'Partial' : 'Flagged';

  return (
    <>
      <motion.button
        whileHover={{ scale: 1.04 }}
        whileTap={{ scale: 0.96 }}
        onClick={() => setOpen(true)}
        style={{
          display: 'inline-flex', alignItems: 'center', gap: 5,
          padding: '3px 9px', borderRadius: 999,
          background: `${color}12`, border: `1px solid ${color}30`,
          fontSize: 11, fontWeight: 700, color: color,
          cursor: 'pointer', fontFamily: "'Inter', sans-serif",
          letterSpacing: '-.01em',
          transition: 'all 0.2s',
        }}
        title="Click to see verification report"
      >
        <Icon style={{ width: 11, height: 11, strokeWidth: 2 }} />
        Trust {trustScore}/100
      </motion.button>

      <AnimatePresence>
        {open && (
          <>
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              onClick={() => setOpen(false)}
              style={{ position: 'fixed', inset: 0, zIndex: 1000, background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(8px)' }}
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
              style={{
                position: 'fixed', top: '50%', left: '50%', transform: 'translate(-50%,-50%)',
                zIndex: 1001, width: '90vw', maxWidth: 560, maxHeight: '80vh',
                background: '#fff', borderRadius: 16,
                boxShadow: '0 30px 80px rgba(0,0,0,0.25), 0 0 0 1px rgba(0,0,0,0.05)',
                display: 'flex', flexDirection: 'column', overflow: 'hidden',
                fontFamily: "'Inter', sans-serif",
              }}>
              {/* Header */}
              <div style={{ padding: '20px 24px', borderBottom: '1px solid #EBEBEB', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div style={{ width: 40, height: 40, borderRadius: 10, background: `${color}10`, border: `1px solid ${color}25`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Icon style={{ width: 18, height: 18, color, strokeWidth: 2 }} />
                  </div>
                  <div>
                    <div style={{ fontSize: 16, fontWeight: 700, color: '#0A0A0A', letterSpacing: '-.01em' }}>
                      Trust Score: <span style={{ color }}>{trustScore}/100</span>
                    </div>
                    <div style={{ fontSize: 12, color: '#888', marginTop: 2 }}>
                      {label} — {stats?.verified_count || 0} verified, {stats?.unverified_count || 0} unverified citations
                    </div>
                  </div>
                </div>
                <button onClick={() => setOpen(false)} style={{ background: 'none', border: 'none', padding: 6, cursor: 'pointer', color: '#888' }}>
                  <X style={{ width: 16, height: 16 }} />
                </button>
              </div>

              {/* Stats grid */}
              {stats && (
                <div style={{ padding: '16px 24px', borderBottom: '1px solid #F5F5F5', display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
                  <div style={{ textAlign: 'center', padding: 12, background: '#FAFAFA', borderRadius: 10 }}>
                    <div style={{ fontSize: 20, fontWeight: 700, color: '#22C55E', letterSpacing: '-.02em' }}>{stats.verified_count || 0}</div>
                    <div style={{ fontSize: 10, color: '#888', marginTop: 2, fontWeight: 600, letterSpacing: '.04em', textTransform: 'uppercase' }}>Verified</div>
                  </div>
                  <div style={{ textAlign: 'center', padding: 12, background: '#FAFAFA', borderRadius: 10 }}>
                    <div style={{ fontSize: 20, fontWeight: 700, color: '#F59E0B', letterSpacing: '-.02em' }}>{stats.unverified_count || 0}</div>
                    <div style={{ fontSize: 10, color: '#888', marginTop: 2, fontWeight: 600, letterSpacing: '.04em', textTransform: 'uppercase' }}>Unverified</div>
                  </div>
                  <div style={{ textAlign: 'center', padding: 12, background: '#FAFAFA', borderRadius: 10 }}>
                    <div style={{ fontSize: 20, fontWeight: 700, color: '#0A0A0A', letterSpacing: '-.02em' }}>{stats.total_citations || 0}</div>
                    <div style={{ fontSize: 10, color: '#888', marginTop: 2, fontWeight: 600, letterSpacing: '.04em', textTransform: 'uppercase' }}>Total</div>
                  </div>
                </div>
              )}

              {/* Notes */}
              {notes && notes.length > 0 && (
                <div style={{ padding: '16px 24px', borderBottom: '1px solid #F5F5F5' }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: '#888', letterSpacing: '.06em', textTransform: 'uppercase', marginBottom: 10 }}>Notes</div>
                  {notes.map((note, i) => (
                    <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 8, fontSize: 13, color: '#444', lineHeight: 1.5 }}>
                      <AlertTriangle style={{ width: 13, height: 13, color: '#F59E0B', flexShrink: 0, marginTop: 3 }} />
                      <span>{note}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Verification report */}
              {verificationReport && (
                <div style={{ flex: 1, padding: '16px 24px', overflowY: 'auto' }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: '#888', letterSpacing: '.06em', textTransform: 'uppercase', marginBottom: 10 }}>Verification Report</div>
                  <pre style={{
                    whiteSpace: 'pre-wrap', fontSize: 12.5, color: '#333',
                    background: '#FAFAFA', padding: 14, borderRadius: 8,
                    fontFamily: "'JetBrains Mono', monospace", lineHeight: 1.6,
                    margin: 0, border: '1px solid #EBEBEB',
                  }}>{verificationReport}</pre>
                </div>
              )}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
