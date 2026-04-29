import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ShieldCheck, Check } from 'lucide-react';

/**
 * TermsAcceptModal — full-viewport gate shown after the user signs in
 * for the first time (per account). Forces explicit acceptance of the
 * Spectr T&C before the app is accessible.
 *
 * Props:
 *   visible         — whether to render
 *   onAccept        — called when user checks the box and presses Continue
 *   userEmail       — displayed in the modal for personalisation
 */
export default function TermsAcceptModal({ visible, onAccept, userEmail }) {
  const [agreed, setAgreed] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleAccept = () => {
    if (!agreed || submitting) return;
    setSubmitting(true);
    // Small tick so the button state reads, then call onAccept
    setTimeout(() => { onAccept && onAccept(); }, 260);
  };

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
          style={{
            position: 'fixed', inset: 0, zIndex: 9998,
            background: 'rgba(10,10,10,0.6)',
            backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            padding: 24,
            fontFamily: "'Inter', sans-serif",
          }}
        >
          <motion.div
            initial={{ opacity: 0, y: 24, scale: 0.97, filter: 'blur(8px)' }}
            animate={{ opacity: 1, y: 0, scale: 1, filter: 'blur(0px)' }}
            exit={{ opacity: 0, y: 12, scale: 0.98 }}
            transition={{ duration: 0.55, ease: [0.16, 1, 0.3, 1] }}
            style={{
              width: '100%', maxWidth: 520,
              background: '#FFFFFF',
              border: '1px solid rgba(0,0,0,0.06)',
              borderRadius: 22,
              boxShadow: '0 40px 80px rgba(0,0,0,0.22), 0 8px 24px rgba(0,0,0,0.08)',
              padding: '40px 40px 32px',
              color: '#0A0A0A',
            }}
          >
            {/* Icon badge */}
            <div style={{
              width: 52, height: 52, borderRadius: 14,
              background: 'linear-gradient(135deg, #0A0A0A, #232323)',
              display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
              marginBottom: 22,
              boxShadow: '0 8px 22px rgba(0,0,0,0.15)',
            }}>
              <ShieldCheck style={{ width: 22, height: 22, color: '#fff', strokeWidth: 1.7 }} />
            </div>

            {/* Eyebrow */}
            <div style={{
              display: 'inline-flex', alignItems: 'center', gap: 6,
              fontSize: 11, fontWeight: 500, color: '#6B7280',
              letterSpacing: '0.22em', textTransform: 'uppercase',
              marginBottom: 12,
            }}>
              One more step
            </div>

            {/* Title */}
            <h2 style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: 28, fontWeight: 500,
              letterSpacing: '-0.045em', lineHeight: 1.1,
              margin: 0, marginBottom: 10,
              background: 'linear-gradient(to bottom right, #0A0A0A 40%, rgba(10,10,10,0.5))',
              WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text',
            }}>
              Accept the Spectr agreement.
            </h2>

            {/* Body */}
            <p style={{
              fontSize: 14, color: '#6B7280', lineHeight: 1.6,
              letterSpacing: '-0.005em', margin: 0, marginBottom: 22,
            }}>
              {userEmail
                ? <>Before you continue, <b style={{ color: '#0A0A0A', fontWeight: 500 }}>{userEmail}</b> needs to review and accept the Terms &amp; Conditions that govern Spectr.</>
                : <>Before you continue, please review and accept the Terms &amp; Conditions that govern Spectr.</>
              }
            </p>

            {/* Checkbox row */}
            <label
              onClick={() => setAgreed(a => !a)}
              style={{
                display: 'flex', alignItems: 'flex-start', gap: 12,
                padding: '14px 16px', marginBottom: 24,
                background: agreed ? 'rgba(10,10,10,0.04)' : '#FAFAFA',
                border: `1px solid ${agreed ? 'rgba(10,10,10,0.18)' : 'rgba(0,0,0,0.08)'}`,
                borderRadius: 12,
                cursor: 'pointer',
                transition: 'all 0.2s',
                userSelect: 'none',
              }}
            >
              {/* Custom checkbox */}
              <div style={{
                width: 18, height: 18, flexShrink: 0, borderRadius: 5,
                border: `1.5px solid ${agreed ? '#0A0A0A' : 'rgba(0,0,0,0.28)'}`,
                background: agreed ? '#0A0A0A' : '#fff',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                marginTop: 1, transition: 'all 0.18s',
              }}>
                {agreed && <Check style={{ width: 12, height: 12, color: '#fff', strokeWidth: 3 }} />}
              </div>
              <span style={{
                fontSize: 13.5, color: '#0A0A0A', lineHeight: 1.55,
                letterSpacing: '-0.005em', fontWeight: 450,
              }}>
                I agree to the&nbsp;
                <a
                  href="/terms"
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={e => e.stopPropagation()}
                  style={{
                    color: '#0A0A0A', fontWeight: 500,
                    textDecoration: 'underline',
                    textDecorationColor: '#0A0A0A',
                    textUnderlineOffset: 3,
                    textDecorationThickness: '1px',
                  }}
                >
                  Terms &amp; Conditions
                </a>
                &nbsp;of Spectr — the AI Legal &amp; Accounting Platform.
              </span>
            </label>

            {/* Action row */}
            <button
              onClick={handleAccept}
              disabled={!agreed || submitting}
              style={{
                width: '100%',
                padding: '14px 20px',
                background: agreed ? '#0A0A0A' : '#E5E7EB',
                color: agreed ? '#fff' : '#9CA3AF',
                fontFamily: "'Inter', sans-serif",
                fontSize: 14, fontWeight: 500, letterSpacing: '-0.01em',
                border: 'none', borderRadius: 12,
                cursor: agreed && !submitting ? 'pointer' : 'not-allowed',
                transition: 'all 0.2s cubic-bezier(0.16,1,0.3,1)',
                boxShadow: agreed ? '0 8px 22px rgba(10,10,10,0.2), inset 0 1px 0 rgba(255,255,255,0.1)' : 'none',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
              }}
              onMouseEnter={e => { if (agreed && !submitting) { e.currentTarget.style.transform = 'translateY(-1px)'; } }}
              onMouseLeave={e => { e.currentTarget.style.transform = 'none'; }}
            >
              {submitting ? (
                <>
                  <div style={{
                    width: 14, height: 14,
                    border: '2px solid rgba(255,255,255,0.3)',
                    borderTopColor: '#fff',
                    borderRadius: '50%',
                    animation: 'spin 0.7s linear infinite',
                  }} />
                  Saving…
                </>
              ) : (
                <>Continue to Spectr</>
              )}
            </button>

            {/* Fine-print footer */}
            <p style={{
              marginTop: 16, fontSize: 11, color: '#9CA3AF',
              lineHeight: 1.5, textAlign: 'center', letterSpacing: '-0.005em',
            }}>
              Your acceptance is logged to your account and dated on our servers.
            </p>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
