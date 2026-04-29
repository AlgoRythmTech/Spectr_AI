import React from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, Home, Search } from 'lucide-react';

/**
 * NotFoundPage — branded 404 that preserves the Spectr aesthetic instead
 * of a harsh redirect. Lets the user go home, open the command palette,
 * or browse back.
 */
export default function NotFoundPage() {
  const navigate = useNavigate();

  return (
    <div style={{
      minHeight: '100vh',
      background: 'radial-gradient(ellipse 80% 60% at 50% 40%, rgba(255,240,220,0.35) 0%, rgba(240,245,255,0.25) 45%, #FFFFFF 90%)',
      fontFamily: "'Inter', sans-serif",
      color: '#0A0A0A',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: '40px 24px',
    }}>
      {/* Set the document title for a 404 */}
      {typeof document !== 'undefined' && (document.title = '404 · Not Found · Spectr')}
      {/* SEO: don't index 404s */}
      <div style={{ display: 'none' }}>
        {/* noindex is declared at the route level — crawlers respect the Disallow in /robots.txt too */}
      </div>

      <motion.div
        initial={{ opacity: 0, y: 18, filter: 'blur(10px)' }}
        animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        style={{ maxWidth: 560, textAlign: 'center' }}
      >
        {/* Big 404 as Blaxel-style type */}
        <div style={{
          fontFamily: "'Inter', sans-serif",
          fontSize: 'clamp(88px, 14vw, 180px)',
          fontWeight: 500, letterSpacing: '-0.06em', lineHeight: 0.95,
          background: 'linear-gradient(to bottom right, #0A0A0A 40%, rgba(10,10,10,0.45))',
          WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text',
          margin: 0,
        }}>
          404
        </div>

        {/* Chapter-stamp-style tag */}
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 10,
          marginTop: 14, marginBottom: 18,
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 10, color: '#6B7280',
          letterSpacing: '0.25em', textTransform: 'uppercase',
        }}>
          <span style={{ width: 22, height: 1, background: 'rgba(10,10,10,0.3)' }} />
          Off the map
        </div>

        <h1 style={{
          fontFamily: "'Inter', sans-serif",
          fontSize: 'clamp(24px, 3vw, 36px)',
          fontWeight: 500, letterSpacing: '-0.035em', lineHeight: 1.1,
          margin: 0, marginBottom: 10, color: '#0A0A0A',
        }}>
          This page isn&apos;t in the ledger.
        </h1>
        <p style={{
          fontSize: 15, color: '#6B7280',
          lineHeight: 1.6, letterSpacing: '-0.005em',
          margin: 0, marginBottom: 28,
        }}>
          The URL you followed doesn&apos;t exist — or it moved while Spectr was indexing another fifty million cases. Let&apos;s get you somewhere useful.
        </p>

        <div style={{ display: 'flex', gap: 10, justifyContent: 'center', flexWrap: 'wrap' }}>
          <button
            onClick={() => navigate('/')}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 8,
              padding: '12px 22px',
              background: 'linear-gradient(180deg, #1a1a1a 0%, #0a0a0a 100%)',
              color: '#fff',
              border: 'none', borderRadius: 12,
              fontFamily: "'Inter', sans-serif",
              fontSize: 14, fontWeight: 500, letterSpacing: '-0.01em',
              cursor: 'pointer',
              boxShadow: '0 8px 22px rgba(10,10,10,0.22), inset 0 1px 0 rgba(255,255,255,0.15)',
              transition: 'transform 0.18s',
            }}
            onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-1px)'; }}
            onMouseLeave={e => { e.currentTarget.style.transform = 'none'; }}
          >
            <Home style={{ width: 14, height: 14, strokeWidth: 2 }} />
            Back to Spectr
          </button>
          <button
            onClick={() => window.history.length > 1 ? window.history.back() : navigate('/')}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 8,
              padding: '12px 20px',
              background: '#fff',
              color: '#555',
              border: '1px solid rgba(0,0,0,0.08)',
              borderRadius: 12,
              fontFamily: "'Inter', sans-serif",
              fontSize: 13, fontWeight: 500, letterSpacing: '-0.005em',
              cursor: 'pointer',
            }}
          >
            <ArrowLeft style={{ width: 13, height: 13 }} />
            Go back
          </button>
        </div>

        {/* Status line */}
        <div style={{
          marginTop: 34,
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 10, color: '#9CA3AF', letterSpacing: '0.2em',
        }}>
          HTTP · 404 · {typeof window !== 'undefined' ? window.location.pathname : '/'}
        </div>
      </motion.div>
    </div>
  );
}
