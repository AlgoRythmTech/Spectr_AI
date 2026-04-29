import React from 'react';

/**
 * Liquid Glass Effect — Apple-style frosted glass with SVG displacement filter.
 * Adapted from TypeScript/Tailwind to plain JS/inline styles for CRA.
 */

/* ─── SVG Filter (render once, hidden) ─── */
export function GlassFilter() {
  return (
    <svg style={{ display: 'none' }} aria-hidden="true">
      <filter
        id="glass-distortion"
        x="0%"
        y="0%"
        width="100%"
        height="100%"
        filterUnits="objectBoundingBox"
      >
        <feTurbulence
          type="fractalNoise"
          baseFrequency="0.001 0.005"
          numOctaves="1"
          seed="17"
          result="turbulence"
        />
        <feComponentTransfer in="turbulence" result="mapped">
          <feFuncR type="gamma" amplitude="1" exponent="10" offset="0.5" />
          <feFuncG type="gamma" amplitude="0" exponent="1" offset="0" />
          <feFuncB type="gamma" amplitude="0" exponent="1" offset="0.5" />
        </feComponentTransfer>
        <feGaussianBlur in="turbulence" stdDeviation="3" result="softMap" />
        <feSpecularLighting
          in="softMap"
          surfaceScale="5"
          specularConstant="1"
          specularExponent="100"
          lightingColor="white"
          result="specLight"
        >
          <fePointLight x="-200" y="-200" z="300" />
        </feSpecularLighting>
        <feComposite
          in="specLight"
          operator="arithmetic"
          k1="0"
          k2="1"
          k3="1"
          k4="0"
          result="litImage"
        />
        <feDisplacementMap
          in="SourceGraphic"
          in2="softMap"
          scale="200"
          xChannelSelector="R"
          yChannelSelector="G"
        />
      </filter>
    </svg>
  );
}

/* ─── Glass Effect Wrapper ─── */
export function GlassEffect({ children, style = {}, onClick }) {
  return (
    <div
      onClick={onClick}
      style={{
        position: 'relative',
        display: 'inline-flex',
        fontWeight: 600,
        overflow: 'hidden',
        cursor: 'pointer',
        transition: 'all 0.7s cubic-bezier(0.175, 0.885, 0.32, 2.2)',
        boxShadow: '0 6px 6px rgba(0, 0, 0, 0.2), 0 0 20px rgba(0, 0, 0, 0.1)',
        borderRadius: 24,
        ...style,
      }}
    >
      {/* Glass distortion layer */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          zIndex: 0,
          overflow: 'hidden',
          borderRadius: 24,
          backdropFilter: 'blur(3px)',
          filter: 'url(#glass-distortion)',
          isolation: 'isolate',
        }}
      />
      {/* White tint layer */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          zIndex: 10,
          borderRadius: 24,
          background: 'rgba(255, 255, 255, 0.25)',
        }}
      />
      {/* Inner glow/shadow layer */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          zIndex: 20,
          borderRadius: 24,
          overflow: 'hidden',
          boxShadow:
            'inset 2px 2px 1px 0 rgba(255, 255, 255, 0.5), inset -1px -1px 1px 1px rgba(255, 255, 255, 0.5)',
        }}
      />
      {/* Content */}
      <div style={{ position: 'relative', zIndex: 30 }}>{children}</div>
    </div>
  );
}

/* ─── Glass Button ─── */
export function GlassButton({ children, onClick, style = {} }) {
  return (
    <GlassEffect
      onClick={onClick}
      style={{
        padding: '16px 36px',
        borderRadius: 16,
        ...style,
      }}
    >
      <div
        style={{
          transition: 'all 0.7s cubic-bezier(0.175, 0.885, 0.32, 2.2)',
        }}
      >
        {children}
      </div>
    </GlassEffect>
  );
}
