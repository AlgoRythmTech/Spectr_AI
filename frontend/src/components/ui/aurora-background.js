import React from 'react';

/**
 * Aurora Background — animated gradient aurora effect.
 * Adapted from TSX/Tailwind to plain JS/inline styles for CRA.
 * Works on both light and dark backgrounds via CSS variables.
 */
export function AuroraBackground({ style = {}, showRadialGradient = true, dark = false }) {
  return (
    <>
      <style>{`
        @keyframes aurora-slide {
          from { background-position: 50% 50%, 50% 50%; }
          to { background-position: 350% 50%, 350% 50%; }
        }
        .aurora-layer {
          --white-g: repeating-linear-gradient(100deg, rgba(255,255,255,1) 0%, rgba(255,255,255,1) 7%, transparent 10%, transparent 12%, rgba(255,255,255,1) 16%);
          --dark-g: repeating-linear-gradient(100deg, rgba(0,0,0,1) 0%, rgba(0,0,0,1) 7%, transparent 10%, transparent 12%, rgba(0,0,0,1) 16%);
          --aurora-g: repeating-linear-gradient(100deg, #3b82f6 10%, #a5b4fc 15%, #93c5fd 20%, #ddd6fe 25%, #60a5fa 30%);
          position: absolute;
          inset: -10px;
          pointer-events: none;
          will-change: transform;
          opacity: 0.5;
          background-image: var(--white-g), var(--aurora-g);
          background-size: 300%, 200%;
          background-position: 50% 50%, 50% 50%;
          filter: blur(10px) invert(1);
        }
        .aurora-layer.dark {
          background-image: var(--dark-g), var(--aurora-g);
          filter: blur(10px);
        }
        .aurora-layer::after {
          content: '';
          position: absolute;
          inset: 0;
          background-image: var(--white-g), var(--aurora-g);
          background-size: 200%, 100%;
          background-attachment: fixed;
          mix-blend-mode: difference;
          animation: aurora-slide 60s linear infinite;
        }
        .aurora-layer.dark::after {
          background-image: var(--dark-g), var(--aurora-g);
        }
        .aurora-mask {
          -webkit-mask-image: radial-gradient(ellipse at 100% 0%, black 10%, transparent 70%);
          mask-image: radial-gradient(ellipse at 100% 0%, black 10%, transparent 70%);
        }
      `}</style>
      <div style={{ position: 'absolute', inset: 0, overflow: 'hidden', ...style }}>
        <div className={`aurora-layer${dark ? ' dark' : ''}${showRadialGradient ? ' aurora-mask' : ''}`} />
      </div>
    </>
  );
}
