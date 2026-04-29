import React from 'react';
import { motion } from 'framer-motion';

/**
 * Pulse Beams — animated SVG gradient beams connecting nodes.
 * Adapted from TypeScript/Tailwind to plain JS/inline styles for CRA.
 */

function GradientColors({ colors }) {
  const c = colors || { start: '#18CCFC', middle: '#6344F5', end: '#AE48FF' };
  return (
    <>
      <stop offset="0%" stopColor={c.start} stopOpacity="0" />
      <stop offset="20%" stopColor={c.start} stopOpacity="1" />
      <stop offset="50%" stopColor={c.middle} stopOpacity="1" />
      <stop offset="100%" stopColor={c.end} stopOpacity="0" />
    </>
  );
}

function SVGs({ beams, width, height, baseColor, accentColor, gradientColors }) {
  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      style={{ flexShrink: 0 }}
    >
      {beams.map((beam, index) => (
        <React.Fragment key={index}>
          <path d={beam.path} stroke={baseColor} strokeWidth="1" />
          <path d={beam.path} stroke={`url(#pgrad${index})`} strokeWidth="2" strokeLinecap="round" />
          {beam.connectionPoints?.map((point, pi) => (
            <circle key={`${index}-${pi}`} cx={point.cx} cy={point.cy} r={point.r} fill={baseColor} stroke={accentColor} />
          ))}
        </React.Fragment>
      ))}
      <defs>
        {beams.map((beam, index) => (
          <motion.linearGradient
            key={index}
            id={`pgrad${index}`}
            gradientUnits="userSpaceOnUse"
            initial={beam.gradientConfig.initial}
            animate={beam.gradientConfig.animate}
            transition={beam.gradientConfig.transition}
          >
            <GradientColors colors={gradientColors} />
          </motion.linearGradient>
        ))}
      </defs>
    </svg>
  );
}

export function PulseBeams({
  children,
  className,
  style = {},
  background,
  beams,
  width = 858,
  height = 434,
  baseColor = 'rgba(255,255,255,0.08)',
  accentColor = 'rgba(255,255,255,0.15)',
  gradientColors,
}) {
  return (
    <div
      className={className}
      style={{
        width: '100%',
        position: 'relative',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        overflow: 'hidden',
        ...style,
      }}
    >
      {background}
      <div style={{ position: 'relative', zIndex: 10 }}>{children}</div>
      <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <SVGs
          beams={beams}
          width={width}
          height={height}
          baseColor={baseColor}
          accentColor={accentColor}
          gradientColors={gradientColors}
        />
      </div>
    </div>
  );
}

/* ─── Pre-configured beams for CTA sections ─── */
export const CTA_BEAMS = [
  {
    path: 'M269 220.5H16.5C10.977 220.5 6.5 224.977 6.5 230.5V398.5',
    gradientConfig: {
      initial: { x1: '0%', x2: '0%', y1: '80%', y2: '100%' },
      animate: { x1: ['0%', '0%', '200%'], x2: ['0%', '0%', '180%'], y1: ['80%', '0%', '0%'], y2: ['100%', '20%', '20%'] },
      transition: { duration: 2, repeat: Infinity, repeatType: 'loop', ease: 'linear', repeatDelay: 2, delay: 0.4 },
    },
    connectionPoints: [{ cx: 6.5, cy: 398.5, r: 6 }, { cx: 269, cy: 220.5, r: 6 }],
  },
  {
    path: 'M568 200H841C846.523 200 851 195.523 851 190V40',
    gradientConfig: {
      initial: { x1: '0%', x2: '0%', y1: '80%', y2: '100%' },
      animate: { x1: ['20%', '100%', '100%'], x2: ['0%', '90%', '90%'], y1: ['80%', '80%', '-20%'], y2: ['100%', '100%', '0%'] },
      transition: { duration: 2, repeat: Infinity, repeatType: 'loop', ease: 'linear', repeatDelay: 2, delay: 1.1 },
    },
    connectionPoints: [{ cx: 851, cy: 34, r: 6.5 }, { cx: 568, cy: 200, r: 6 }],
  },
  {
    path: 'M425.5 274V333C425.5 338.523 421.023 343 415.5 343H152C146.477 343 142 347.477 142 353V426.5',
    gradientConfig: {
      initial: { x1: '0%', x2: '0%', y1: '80%', y2: '100%' },
      animate: { x1: ['20%', '100%', '100%'], x2: ['0%', '90%', '90%'], y1: ['80%', '80%', '-20%'], y2: ['100%', '100%', '0%'] },
      transition: { duration: 2, repeat: Infinity, repeatType: 'loop', ease: 'linear', repeatDelay: 2, delay: 0.7 },
    },
    connectionPoints: [{ cx: 142, cy: 427, r: 6.5 }, { cx: 425.5, cy: 274, r: 6 }],
  },
  {
    path: 'M493 274V333.226C493 338.749 497.477 343.226 503 343.226H760C765.523 343.226 770 347.703 770 353.226V427',
    gradientConfig: {
      initial: { x1: '40%', x2: '50%', y1: '160%', y2: '180%' },
      animate: { x1: '0%', x2: '10%', y1: '-40%', y2: '-20%' },
      transition: { duration: 2, repeat: Infinity, repeatType: 'loop', ease: 'linear', repeatDelay: 2, delay: 1.5 },
    },
    connectionPoints: [{ cx: 770, cy: 427, r: 6.5 }, { cx: 493, cy: 274, r: 6 }],
  },
  {
    path: 'M380 168V17C380 11.477 384.477 7 390 7H414',
    gradientConfig: {
      initial: { x1: '-40%', x2: '-10%', y1: '0%', y2: '20%' },
      animate: { x1: ['40%', '0%', '0%'], x2: ['10%', '0%', '0%'], y1: ['0%', '0%', '180%'], y2: ['20%', '20%', '200%'] },
      transition: { duration: 2, repeat: Infinity, repeatType: 'loop', ease: 'linear', repeatDelay: 2, delay: 0.2 },
    },
    connectionPoints: [{ cx: 420.5, cy: 6.5, r: 6 }, { cx: 380, cy: 168, r: 6 }],
  },
];
