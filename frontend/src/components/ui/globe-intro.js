import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

/**
 * India Map Intro — no curtains, clean fade reveal
 *
 * Sequence:
 *   0-0.8s   → Map fades in
 *   0.8-2.8s → Map zooms in + cities pulse in
 *   2.8-4.8s → "Built for India." fades in, map holds
 *   4.8-6.0s → Smooth fade-out, website revealed
 */

export function GlobeIntro({ onComplete }) {
  const [phase, setPhase] = useState('intro');

  useEffect(() => {
    // Lock body scroll while intro plays so scrolls don't accumulate on landing page behind
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    const t1 = setTimeout(() => setPhase('zooming'), 800);    // start zoom
    const t2 = setTimeout(() => setPhase('arrived'), 2800);   // text appears
    const t3 = setTimeout(() => setPhase('fadeout'), 4800);   // start fade
    const t4 = setTimeout(() => {
      setPhase('done');
      // Reset scroll to top so landing page is at top when revealed
      window.scrollTo(0, 0);
      onComplete?.();
    }, 5600); // done (0.8s fade)

    return () => {
      [t1, t2, t3, t4].forEach(clearTimeout);
      document.body.style.overflow = prevOverflow;
    };
  }, [onComplete]);

  const handleSkip = () => {
    setPhase('fadeout');
    setTimeout(() => {
      setPhase('done');
      window.scrollTo(0, 0);
      onComplete?.();
    }, 800);
  };

  if (phase === 'done') return null;

  const mapScale =
    phase === 'intro'   ? 1.0 :
    phase === 'zooming' ? 1.4 :
    phase === 'arrived' ? 1.55 :
    phase === 'fadeout' ? 1.7 :
    1.0;

  const showText = phase === 'arrived' || phase === 'fadeout';
  const fading = phase === 'fadeout';

  return (
    <motion.div
      initial={{ opacity: 1 }}
      animate={{ opacity: fading ? 0 : 1 }}
      transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
      style={{
        position: 'fixed', inset: 0, zIndex: 9999,
        background: '#fff',
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        fontFamily: "'Inter', 'Plus Jakarta Sans', sans-serif",
        overflow: 'hidden',
        pointerEvents: fading ? 'none' : 'auto',
      }}
    >
      <style>{`
        @keyframes city-ping {
          0% { transform: scale(1); opacity: 0.7; }
          100% { transform: scale(2.5); opacity: 0; }
        }
      `}</style>

      {/* Grid backdrop */}
      <div style={{
        position: 'absolute', inset: 0,
        backgroundImage: 'linear-gradient(rgba(10,10,10,0.04) 1px,transparent 1px),linear-gradient(90deg,rgba(10,10,10,0.04) 1px,transparent 1px)',
        backgroundSize: '60px 60px',
        maskImage: 'radial-gradient(ellipse at center, black 30%, transparent 70%)',
        WebkitMaskImage: 'radial-gradient(ellipse at center, black 30%, transparent 70%)',
        pointerEvents: 'none',
      }} />

      {/* India map */}
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: mapScale }}
        transition={{
          opacity: { duration: 0.8 },
          scale: { duration: 2.0, ease: [0.22, 1, 0.36, 1] },
        }}
        style={{
          width: 'min(420px, 50vw)',
          maxHeight: '60vh',
          position: 'relative',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginTop: '-5vh',
        }}
      >
        <img
          src="/india-map.svg"
          alt="India"
          style={{
            width: '100%', height: 'auto',
            filter: 'brightness(0) invert(0.15)',
            pointerEvents: 'none',
            userSelect: 'none',
          }}
          draggable={false}
        />
        {phase !== 'intro' && [
          { left: '48%', top: '18%' },
          { left: '33%', top: '55%' },
          { left: '45%', top: '75%' },
          { left: '52%', top: '80%' },
          { left: '46%', top: '65%' },
          { left: '70%', top: '45%' },
        ].map((pos, i) => (
          <motion.div key={i}
            initial={{ opacity: 0, scale: 0 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2 + i * 0.08, duration: 0.4 }}
            style={{
              position: 'absolute', left: pos.left, top: pos.top,
              width: 9, height: 9, borderRadius: '50%',
              background: '#DC2626',
              boxShadow: '0 0 10px rgba(220,38,38,0.6)',
              transform: 'translate(-50%,-50%)',
            }}
          >
            <span style={{
              position: 'absolute', inset: 0, borderRadius: '50%',
              border: '1.5px solid #DC2626',
              animation: `city-ping 2s ease-out infinite ${i * 0.3}s`,
            }} />
          </motion.div>
        ))}
      </motion.div>

      {/* Built for India */}
      <AnimatePresence>
        {showText && (
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
            style={{
              position: 'absolute',
              bottom: 'clamp(10%, 15vh, 22%)',
              textAlign: 'center',
              width: '90%', maxWidth: 760,
            }}
          >
            <motion.p
              initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              transition={{ delay: 0.15, duration: 0.4 }}
              style={{
                fontSize: 11, fontWeight: 700, letterSpacing: '.25em',
                color: 'rgba(10,10,10,0.5)', textTransform: 'uppercase', marginBottom: 14,
                fontFamily: "'Plus Jakarta Sans', sans-serif",
              }}
            >🇮🇳 &nbsp; Spectr</motion.p>
            <motion.h1
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
              style={{
                fontFamily: "'Inter', sans-serif",
                fontSize: 'clamp(44px, 7vw, 92px)',
                fontWeight: 500,
                background: 'linear-gradient(to bottom right, #0A0A0A 40%, rgba(10,10,10,0.45))',
                WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
                letterSpacing: '-.05em', lineHeight: 1, margin: 0,
              }}
            >Built for India.</motion.h1>
            <motion.p
              initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              transition={{ delay: 0.4, duration: 0.4 }}
              style={{
                fontSize: 'clamp(14px, 1.4vw, 17px)',
                color: 'rgba(10,10,10,0.45)',
                marginTop: 16, fontWeight: 400,
                fontFamily: "'Plus Jakarta Sans', sans-serif",
              }}
            >AI-native legal intelligence, engineered for Indian law.</motion.p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Skip */}
      <motion.button
        initial={{ opacity: 0 }}
        animate={{ opacity: phase === 'intro' ? 0 : 0.4 }}
        whileHover={{ opacity: 0.9 }}
        onClick={handleSkip}
        style={{
          position: 'absolute', top: 24, right: 24,
          background: 'transparent', border: '1px solid rgba(10,10,10,0.12)', color: '#0A0A0A',
          fontSize: 11, fontWeight: 600, letterSpacing: '.08em',
          cursor: 'pointer', padding: '8px 14px', borderRadius: 8,
          fontFamily: "'Plus Jakarta Sans', sans-serif",
          textTransform: 'uppercase', zIndex: 20,
        }}
      >Skip →</motion.button>
    </motion.div>
  );
}
