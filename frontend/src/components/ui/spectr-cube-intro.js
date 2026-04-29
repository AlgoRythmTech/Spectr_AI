import React, { useEffect, useState, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

/**
 * SpectrCubeIntro — "Built for India" cinema-verité intro.
 *
 * A ~15-second film-quality opener: eight long-held scenes, each a single
 * clear photo with a parallax dolly, a chapter stamp, and a minimal caption.
 * Ends on a clean brand title card with tagline.
 *
 * Export name `SpectrCubeIntro` is preserved so LandingPage's import
 * doesn't need to change.
 */

// ─── Curated photo palette (all verified 200 OK, richer than stock) ───
const IMG = {
  // LAW — classical, moody, architectural
  architecture:  'https://images.unsplash.com/photo-1453928582365-b6ad33cbcf64?auto=format&fit=crop&w=1800&q=85', // classical statues / authority
  libraryLamp:   'https://images.unsplash.com/photo-1541872703-74c5e44368f9?auto=format&fit=crop&w=1800&q=85',   // reading-lamp library
  gavel:         'https://images.unsplash.com/photo-1589994965851-a8f479c573a9?auto=format&fit=crop&w=1800&q=85', // gavel on law books
  bookRows:      'https://images.unsplash.com/photo-1505664194779-8beaceb93744?auto=format&fit=crop&w=1800&q=85', // rows of law books
  colonnade:     'https://images.unsplash.com/photo-1529107386315-e1a2ed48a620?auto=format&fit=crop&w=1800&q=85', // arched colonnade
  // ACCOUNTING — currency / ledger / close-ups
  currency:      'https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=1800&q=85', // currency close-up
  ledger:        'https://images.unsplash.com/photo-1567427017947-545c5f8d16ad?auto=format&fit=crop&w=1800&q=85', // ledger + charts
  vault:         'https://images.unsplash.com/photo-1579227114347-15d08fc37cae?auto=format&fit=crop&w=1800&q=85', // vault / bank architecture
  // CLOSING — cinematic / city
  skylineNight:  'https://images.unsplash.com/photo-1470549638415-0a0755be0619?auto=format&fit=crop&w=1800&q=85', // moody cityscape
};
const ALL_IMAGES = Object.values(IMG);

// ─── The sequence: eight deliberate scenes, one count-up, one brand card ───
// ─── Ticker items for the letterbox news-crawl ───
const TICKER_ITEMS = [
  'SC 2024', 'VODAFONE IDEA v. UoI', '§ 420 IPC → § 318 BNS', 'ITAT MUMBAI 2024/127',
  'CESTAT DELHI', '§ 194T TDS w.e.f. 01-10-2024', 'CBIC CIRCULAR 213/7/2024-GST',
  'SEBI (LODR) REG 2015', 'RBI MASTER DIRECTION 2024-25/132', 'K.S. PUTTASWAMY v. UoI',
  'NCLT DELHI BENCH', 'FORM 26AS RECONCILIATION', 'GSTR-2B ITC MISMATCH',
  'ADVANCE TAX Q2 · 15-SEP', '§ 40A(3) CASH LIMIT', 'TRANSFER PRICING · FORM 3CEB',
];

const SEQUENCE = [
  { kind: 'scene', img: IMG.architecture, chapter: '01 / AUTHORITY',            caption: 'The law lives here.',                hold: 1900 },
  { kind: 'scene', img: IMG.libraryLamp,  chapter: '02 / INDEXED',              caption: 'Every judgment. Every statute.',     hold: 2000 },
  { kind: 'scene', img: IMG.gavel,        chapter: '03 / VERIFIED',             caption: 'Every citation, traced to source.',  hold: 2000 },
  { kind: 'scene', img: IMG.currency,     chapter: '04 / GST · TDS · ITR',      caption: 'Every return, reconciled.',          hold: 2000 },
  { kind: 'scene', img: IMG.ledger,       chapter: '05 / TALLY · MCA · CBDT',   caption: 'Every notice, answered.',            hold: 2000 },
  { kind: 'count', img: IMG.bookRows,     chapter: '06 / AT SCALE',             value: 50000000, suffix: 'M+', label: 'JUDGMENTS · STATUTES · CIRCULARS',  hold: 2600 },
  { kind: 'scene', img: IMG.colonnade,    chapter: '07 / ONE PLATFORM',         caption: 'Law & Accounting, unified.',         hold: 2000 },
  { kind: 'brand', img: IMG.skylineNight,                                                                                       hold: 2600 },
];

const EXIT_FADE_MS = 580;

/* ═══════════════════════════════════════════════════════════════
   SCENE — full-bleed photo with chapter stamp + caption + crosshair
═══════════════════════════════════════════════════════════════ */
function Scene({ beat, beatIdx }) {
  return (
    <motion.div
      key={`scene-${beatIdx}`}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.75, ease: [0.22, 1, 0.36, 1] }}
      style={{ position: 'absolute', inset: 0, overflow: 'hidden', zIndex: 2 }}
    >
      {/* Slow parallax dolly */}
      <motion.img
        src={beat.img}
        alt=""
        initial={{ scale: 1.06, x: -8, y: 0 }}
        animate={{ scale: 1.18, x: 8, y: -6 }}
        transition={{ duration: beat.hold / 1000 + 1, ease: 'linear' }}
        style={{
          position: 'absolute', inset: 0,
          width: '100%', height: '100%',
          objectFit: 'cover',
          filter: 'brightness(0.62) contrast(1.1) saturate(0.95)',
        }}
      />
      {/* Legibility vignette */}
      <div style={{
        position: 'absolute', inset: 0, pointerEvents: 'none',
        background: 'linear-gradient(to top, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0.35) 45%, rgba(0,0,0,0.2) 70%, rgba(0,0,0,0.55) 100%)',
      }} />
      {/* Teal-orange cinema grade */}
      <div style={{
        position: 'absolute', inset: 0, pointerEvents: 'none',
        background: 'linear-gradient(135deg, rgba(255,150,80,0.05) 0%, rgba(0,0,0,0) 40%, rgba(0,0,0,0) 60%, rgba(40,90,130,0.12) 100%)',
        mixBlendMode: 'overlay',
      }} />

      {/* Chapter stamp top-left */}
      <motion.div
        initial={{ opacity: 0, x: -10 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.25, duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        style={{
          position: 'absolute', top: 90, left: 56,
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 11, fontWeight: 500,
          color: 'rgba(255,255,255,0.72)',
          letterSpacing: '0.25em',
          display: 'flex', alignItems: 'center', gap: 12,
          zIndex: 5,
        }}
      >
        <span style={{ width: 22, height: 1, background: 'rgba(255,220,170,0.8)' }} />
        {beat.chapter}
      </motion.div>

      {/* Big caption bottom-left — words reveal individually */}
      <div style={{
        position: 'absolute', bottom: 110, left: 56, right: 56,
        maxWidth: 880, zIndex: 5, pointerEvents: 'none',
      }}>
        <div style={{
          fontFamily: "'Inter', sans-serif",
          fontSize: 'clamp(40px, 5.8vw, 88px)',
          fontWeight: 500,
          lineHeight: 1.02,
          letterSpacing: '-0.045em',
          color: '#fff',
          textShadow: '0 2px 30px rgba(0,0,0,0.6)',
          display: 'flex', flexWrap: 'wrap', gap: '0.28em',
        }}>
          {beat.caption.split(' ').map((word, i) => (
            <motion.span
              key={`${beatIdx}-${i}`}
              initial={{ opacity: 0, y: 22, filter: 'blur(10px)' }}
              animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
              transition={{
                delay: 0.45 + i * 0.09,
                duration: 0.75,
                ease: [0.16, 1, 0.3, 1],
              }}
              style={{ display: 'inline-block' }}
            >
              {word}
            </motion.span>
          ))}
        </div>
      </div>

      {/* Crosshair reticle top-right */}
      <motion.div
        initial={{ opacity: 0, scale: 0.7 }}
        animate={{ opacity: 0.5, scale: 1 }}
        transition={{ delay: 0.6, duration: 0.5 }}
        style={{
          position: 'absolute', top: 88, right: 56,
          width: 18, height: 18, zIndex: 5, pointerEvents: 'none',
        }}
      >
        <div style={{ position: 'absolute', top: 0, left: '50%', width: 1, height: '100%', background: 'rgba(255,255,255,0.55)' }} />
        <div style={{ position: 'absolute', left: 0, top: '50%', width: '100%', height: 1, background: 'rgba(255,255,255,0.55)' }} />
        <div style={{ position: 'absolute', inset: 0, border: '1px solid rgba(255,255,255,0.4)', borderRadius: '50%' }} />
      </motion.div>
    </motion.div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   COUNT — huge number tick-up over dim photo
═══════════════════════════════════════════════════════════════ */
function CountScene({ beat, beatIdx }) {
  const [n, setN] = useState(0);
  useEffect(() => {
    let raf;
    const start = performance.now();
    const dur = Math.min(beat.hold * 0.8, 1900);
    const tick = (t) => {
      const p = Math.min(1, (t - start) / dur);
      const eased = 1 - Math.pow(1 - p, 3);
      setN(eased * beat.value);
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [beat.value, beat.hold]);

  const display = beat.value >= 1000000
    ? `${(n / 1000000).toFixed(n === beat.value ? 0 : 1)}`
    : `${Math.round(n)}`;

  return (
    <motion.div
      key={`count-${beatIdx}`}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
      style={{ position: 'absolute', inset: 0, overflow: 'hidden', zIndex: 2 }}
    >
      <motion.img
        src={beat.img}
        alt=""
        initial={{ scale: 1.08 }}
        animate={{ scale: 1.2 }}
        transition={{ duration: beat.hold / 1000 + 1, ease: 'linear' }}
        style={{
          position: 'absolute', inset: 0,
          width: '100%', height: '100%',
          objectFit: 'cover',
          filter: 'brightness(0.42) contrast(1.2) blur(2px)',
        }}
      />
      <div style={{
        position: 'absolute', inset: 0, pointerEvents: 'none',
        background: 'radial-gradient(ellipse at 50% 50%, rgba(0,0,0,0.15) 0%, rgba(0,0,0,0.75) 60%, rgba(0,0,0,0.95) 100%)',
      }} />

      <motion.div
        initial={{ opacity: 0, x: -10 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.25, duration: 0.6 }}
        style={{
          position: 'absolute', top: 90, left: 56,
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 11, fontWeight: 500,
          color: 'rgba(255,255,255,0.72)',
          letterSpacing: '0.25em',
          display: 'flex', alignItems: 'center', gap: 12, zIndex: 5,
        }}
      >
        <span style={{ width: 22, height: 1, background: 'rgba(255,220,170,0.8)' }} />
        {beat.chapter}
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20, filter: 'blur(14px)' }}
        animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
        transition={{ delay: 0.3, duration: 1.0, ease: [0.16, 1, 0.3, 1] }}
        style={{
          position: 'absolute', inset: 0, zIndex: 5, pointerEvents: 'none',
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
          gap: 18,
        }}
      >
        <div style={{
          fontFamily: "'Inter', sans-serif",
          fontSize: 'clamp(120px, 20vw, 340px)',
          fontWeight: 500,
          letterSpacing: '-0.06em',
          lineHeight: 0.85,
          color: '#fff',
          fontVariantNumeric: 'tabular-nums',
          textShadow: '0 0 80px rgba(255,230,180,0.22)',
        }}>
          {display}<span style={{ fontSize: '0.55em', opacity: 0.8, marginLeft: 6 }}>{beat.suffix}</span>
        </div>
        <div style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 'clamp(11px, 1.1vw, 13px)',
          fontWeight: 500,
          color: 'rgba(255,255,255,0.6)',
          letterSpacing: '0.28em',
          textAlign: 'center',
        }}>
          {beat.label}
        </div>
      </motion.div>
    </motion.div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   BRAND — final Spectr wordmark with layered reveal
═══════════════════════════════════════════════════════════════ */
function BrandScene({ beat, beatIdx }) {
  return (
    <motion.div
      key={`brand-${beatIdx}`}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
      style={{ position: 'absolute', inset: 0, overflow: 'hidden', zIndex: 2 }}
    >
      <motion.img
        src={beat.img}
        alt=""
        initial={{ scale: 1.12 }}
        animate={{ scale: 1.22 }}
        transition={{ duration: beat.hold / 1000 + 1, ease: 'linear' }}
        style={{
          position: 'absolute', inset: 0, width: '100%', height: '100%',
          objectFit: 'cover',
          filter: 'brightness(0.28) contrast(1.25) blur(6px)',
        }}
      />
      <div style={{
        position: 'absolute', inset: 0,
        background: 'radial-gradient(ellipse at 50% 50%, rgba(0,0,0,0.2) 0%, rgba(0,0,0,0.85) 100%)',
      }} />

      <motion.div
        initial={{ opacity: 0, x: -10 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.2, duration: 0.6 }}
        style={{
          position: 'absolute', top: 90, left: 56,
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 11, fontWeight: 500,
          color: 'rgba(255,255,255,0.72)',
          letterSpacing: '0.25em',
          display: 'flex', alignItems: 'center', gap: 12, zIndex: 5,
        }}
      >
        <span style={{ width: 22, height: 1, background: 'rgba(255,220,170,0.8)' }} />
        08 / SPECTR
      </motion.div>

      <div style={{
        position: 'absolute', inset: 0, zIndex: 5,
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        gap: 22, pointerEvents: 'none',
      }}>
        <motion.h1
          initial={{ opacity: 0, scale: 0.82, filter: 'blur(24px)', letterSpacing: '0.1em' }}
          animate={{ opacity: 1, scale: 1, filter: 'blur(0px)', letterSpacing: '-0.06em' }}
          transition={{ duration: 1.4, ease: [0.16, 1, 0.3, 1] }}
          style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: 'clamp(120px, 18vw, 320px)',
            fontWeight: 500,
            lineHeight: 0.88,
            margin: 0,
            color: '#fff',
            textShadow: '0 0 120px rgba(255,240,210,0.28)',
          }}
        >
          Spectr.
        </motion.h1>
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.9, duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
          style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: 'clamp(13px, 1.3vw, 16px)',
            fontWeight: 400,
            color: 'rgba(255,255,255,0.6)',
            letterSpacing: '0.45em',
            textTransform: 'uppercase',
          }}
        >
          Law &nbsp;&amp;&nbsp; Accounting
        </motion.div>
        <motion.div
          initial={{ scaleX: 0, opacity: 0 }}
          animate={{ scaleX: 1, opacity: 0.65 }}
          transition={{ delay: 1.1, duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
          style={{
            width: 'clamp(160px, 24vw, 400px)',
            height: 1,
            background: 'linear-gradient(to right, transparent, rgba(255,220,170,0.95), transparent)',
            transformOrigin: 'center',
          }}
        />
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.3, duration: 0.6 }}
          style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: 'clamp(12px, 1.1vw, 14px)',
            fontWeight: 400,
            color: 'rgba(255,255,255,0.45)',
            letterSpacing: '-0.01em',
            textAlign: 'center',
            maxWidth: 540,
            marginTop: 4,
          }}
        >
          Built for India. By India.
        </motion.div>
      </div>
    </motion.div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Ambient particles — 24 subtle warm motes
═══════════════════════════════════════════════════════════════ */
function ParticleField() {
  const particles = useRef(
    Array.from({ length: 24 }).map((_, i) => ({
      id: i,
      x: Math.random() * 100,
      y: Math.random() * 100,
      size: 1 + Math.random() * 2.5,
      delay: -Math.random() * 20,
      duration: 22 + Math.random() * 22,
    }))
  ).current;
  return (
    <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 6, overflow: 'hidden' }}>
      {particles.map(p => (
        <div key={p.id} style={{
          position: 'absolute',
          left: `${p.x}%`, top: `${p.y}%`,
          width: p.size, height: p.size, borderRadius: '50%',
          background: 'rgba(255,220,170,0.5)',
          boxShadow: `0 0 ${p.size * 3}px rgba(255,220,170,0.55)`,
          animation: `s3d-particle ${p.duration}s linear infinite`,
          animationDelay: `${p.delay}s`,
          opacity: 0.5,
        }} />
      ))}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Film HUD — REC / TC / format strip
═══════════════════════════════════════════════════════════════ */
function FilmHUD({ beatIdx }) {
  const [frame, setFrame] = useState(0);
  useEffect(() => {
    const iv = setInterval(() => setFrame(f => (f + 1) % 24), 1000 / 24);
    return () => clearInterval(iv);
  }, []);
  const ms = SEQUENCE.slice(0, beatIdx).reduce((a, b) => a + b.hold, 0) + frame * 41;
  const s = Math.floor(ms / 1000) % 60;
  const mm = Math.floor(ms / 60000);
  const tc = `${String(mm).padStart(2, '0')}:${String(s).padStart(2, '0')}:${String(frame).padStart(2, '0')}`;
  return (
    <>
      <motion.div
        initial={{ opacity: 0 }} animate={{ opacity: 0.65 }} transition={{ delay: 0.4, duration: 0.5 }}
        style={{
          position: 'absolute', top: 14, left: 22, zIndex: 55, pointerEvents: 'none',
          display: 'flex', alignItems: 'center', gap: 8,
          fontFamily: "'JetBrains Mono', monospace", fontSize: 10,
          color: 'rgba(255,255,255,0.62)', letterSpacing: '0.22em',
        }}
      >
        <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#ef4444', boxShadow: '0 0 8px rgba(239,68,68,0.85)', animation: 's3d-rec-blink 1.4s ease-in-out infinite' }} />
        REC
      </motion.div>
      <motion.div
        initial={{ opacity: 0 }} animate={{ opacity: 0.55 }} transition={{ delay: 0.4, duration: 0.5 }}
        style={{
          position: 'absolute', top: 14, right: 24, zIndex: 55, pointerEvents: 'none',
          fontFamily: "'JetBrains Mono', monospace", fontSize: 10,
          color: 'rgba(255,255,255,0.55)', letterSpacing: '0.15em', fontVariantNumeric: 'tabular-nums',
        }}
      >
        TC {tc}
      </motion.div>
      <motion.div
        initial={{ opacity: 0 }} animate={{ opacity: 0.4 }} transition={{ delay: 0.6, duration: 0.5 }}
        style={{
          position: 'absolute', bottom: 14, right: 24, zIndex: 55, pointerEvents: 'none',
          fontFamily: "'JetBrains Mono', monospace", fontSize: 9,
          color: 'rgba(255,255,255,0.42)', letterSpacing: '0.22em',
        }}
      >
        24 FPS · 2.39:1 · SCOPE
      </motion.div>
    </>
  );
}

/* ═══════════════════════════════════════════════════════════════
   MAIN COMPONENT
═══════════════════════════════════════════════════════════════ */
export function SpectrCubeIntro({ onComplete, onStartExit }) {
  const [beatIdx, setBeatIdx] = useState(0);
  const [exiting, setExiting] = useState(false);

  const dismiss = useCallback(() => {
    setExiting(true);
    onStartExit && onStartExit();
    setTimeout(() => { onComplete && onComplete(); }, EXIT_FADE_MS);
  }, [onComplete, onStartExit]);

  useEffect(() => {
    ALL_IMAGES.forEach(src => { const img = new Image(); img.src = src; });
  }, []);

  useEffect(() => {
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    window.scrollTo(0, 0);

    let idx = 0;
    const timers = [];
    const advance = () => {
      if (idx >= SEQUENCE.length - 1) {
        setExiting(true);
        onStartExit && onStartExit();
        timers.push(setTimeout(() => { onComplete && onComplete(); }, EXIT_FADE_MS));
        return;
      }
      idx += 1;
      setBeatIdx(idx);
      timers.push(setTimeout(advance, SEQUENCE[idx].hold));
    };
    timers.push(setTimeout(advance, SEQUENCE[0].hold));

    const skip = () => dismiss();
    window.addEventListener('keydown', skip);
    window.addEventListener('click', skip);

    return () => {
      timers.forEach(clearTimeout);
      window.removeEventListener('keydown', skip);
      window.removeEventListener('click', skip);
      document.body.style.overflow = prevOverflow;
    };
  }, [dismiss, onComplete, onStartExit]);

  const beat = SEQUENCE[beatIdx];

  return (
    <motion.div
      initial={{ opacity: 1, scale: 1 }}
      animate={{
        opacity: exiting ? 0 : 1,
        filter: exiting ? 'blur(14px)' : 'blur(0px)',
        scale: exiting ? 1.04 : 1,
      }}
      transition={{ duration: EXIT_FADE_MS / 1000, ease: [0.22, 1, 0.36, 1] }}
      style={{
        position: 'fixed', inset: 0, zIndex: 99999,
        background: '#000', overflow: 'hidden', cursor: 'pointer',
        transformOrigin: '50% 50%',
      }}
    >
      {/* Film grain */}
      <div style={{
        position: 'absolute', inset: 0, zIndex: 30, pointerEvents: 'none',
        opacity: 0.14, mixBlendMode: 'overlay',
        backgroundImage: `url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='240' height='240'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 0 0 0 0.55 0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>")`,
        backgroundSize: '240px 240px',
        animation: 's3d-grain-shift 0.7s steps(4) infinite',
      }} />

      {/* Edge vignette */}
      <div style={{
        position: 'absolute', inset: 0, zIndex: 31, pointerEvents: 'none',
        background: 'radial-gradient(ellipse at 50% 50%, rgba(0,0,0,0) 60%, rgba(0,0,0,0.35) 92%, rgba(0,0,0,0.65) 100%)',
      }} />

      {/* Letterbox bars */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0,
        height: 68, background: '#000', zIndex: 50, pointerEvents: 'none',
        transform: exiting ? 'translateY(-100%)' : 'translateY(0)',
        transition: exiting
          ? 'transform 0.4s cubic-bezier(0.7, 0, 0.84, 0)'
          : 'transform 1.1s cubic-bezier(0.16, 1, 0.3, 1)',
        animation: !exiting ? 'fadeIn 1s cubic-bezier(0.16, 1, 0.3, 1) backwards' : 'none',
        boxShadow: '0 8px 18px rgba(0,0,0,0.7)',
      }} />
      <div style={{
        position: 'absolute', bottom: 0, left: 0, right: 0,
        height: 68, background: '#000', zIndex: 50, pointerEvents: 'none',
        transform: exiting ? 'translateY(100%)' : 'translateY(0)',
        transition: exiting
          ? 'transform 0.4s cubic-bezier(0.7, 0, 0.84, 0)'
          : 'transform 1.1s cubic-bezier(0.16, 1, 0.3, 1)',
        animation: !exiting ? 'fadeIn 1s cubic-bezier(0.16, 1, 0.3, 1) backwards' : 'none',
        boxShadow: '0 -8px 18px rgba(0,0,0,0.7)',
        overflow: 'hidden',
      }}>
        {/* Subtle news-crawl ticker inside the bottom letterbox */}
        <div style={{
          position: 'absolute', top: '50%', left: 0, right: 0,
          transform: 'translateY(-50%)', height: 14, overflow: 'hidden',
          maskImage: 'linear-gradient(90deg, transparent 0%, #000 8%, #000 92%, transparent 100%)',
          WebkitMaskImage: 'linear-gradient(90deg, transparent 0%, #000 8%, #000 92%, transparent 100%)',
        }}>
          <div style={{
            display: 'flex', gap: 42, whiteSpace: 'nowrap',
            animation: 's3d-ticker-crawl 70s linear infinite',
          }}>
            {[...TICKER_ITEMS, ...TICKER_ITEMS, ...TICKER_ITEMS].map((t, i) => (
              <span key={i} style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 9.5, fontWeight: 500,
                color: 'rgba(255,220,170,0.55)',
                letterSpacing: '0.16em',
                textTransform: 'uppercase',
                display: 'inline-flex', alignItems: 'center', gap: 14,
              }}>
                {t}
                <span style={{ width: 3, height: 3, borderRadius: '50%', background: 'rgba(255,220,170,0.45)' }} />
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Scene-change white flash — brief film cut, fires on every beatIdx change */}
      <motion.div
        key={`flash-${beatIdx}`}
        initial={{ opacity: 0.35 }}
        animate={{ opacity: 0 }}
        transition={{ duration: 0.14, ease: 'easeOut' }}
        style={{
          position: 'absolute', inset: 0, background: '#fff',
          pointerEvents: 'none', zIndex: 48,
        }}
      />

      {/* Exit bloom */}
      <motion.div
        initial={false}
        animate={exiting ? { opacity: [0, 0.85, 0], scale: [0.3, 1.6, 3.2] } : { opacity: 0, scale: 0.3 }}
        transition={{ duration: 0.55, ease: [0.4, 0, 0.2, 1], times: [0, 0.35, 1] }}
        style={{
          position: 'absolute', top: '50%', left: '50%',
          width: '70vmax', height: '70vmax', transform: 'translate(-50%, -50%)',
          background: 'radial-gradient(circle at 50% 50%, rgba(255,240,210,0.85) 0%, rgba(255,210,150,0.5) 20%, rgba(255,180,90,0.2) 45%, rgba(0,0,0,0) 65%)',
          mixBlendMode: 'screen', pointerEvents: 'none', zIndex: 60, filter: 'blur(40px)',
        }}
      />
      <motion.div
        initial={false}
        animate={exiting ? { opacity: [0, 0.26, 0] } : { opacity: 0 }}
        transition={{ duration: 0.42, ease: 'easeOut', times: [0, 0.4, 1] }}
        style={{ position: 'absolute', inset: 0, background: '#fff', pointerEvents: 'none', zIndex: 61 }}
      />

      <FilmHUD beatIdx={beatIdx} />
      <ParticleField />

      <AnimatePresence mode="sync">
        {beat.kind === 'scene' && <Scene key={`s-${beatIdx}`} beat={beat} beatIdx={beatIdx} />}
        {beat.kind === 'count' && <CountScene key={`c-${beatIdx}`} beat={beat} beatIdx={beatIdx} />}
        {beat.kind === 'brand' && <BrandScene key={`b-${beatIdx}`} beat={beat} beatIdx={beatIdx} />}
      </AnimatePresence>

      {/* Skip hint */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: exiting ? 0 : 0.4 }}
        transition={{ delay: 1.2, duration: 0.4 }}
        style={{
          position: 'absolute', bottom: 86, right: 24,
          fontFamily: "'Inter', sans-serif", fontSize: 10, color: '#fff',
          letterSpacing: '0.22em', textTransform: 'uppercase',
          pointerEvents: 'none', zIndex: 53,
        }}
      >
        Click or any key to skip
      </motion.div>

      {/* Chapter dots — one per beat, Criterion-style */}
      <div style={{
        position: 'absolute', bottom: 82, left: '50%', transform: 'translateX(-50%)',
        display: 'flex', gap: 14, zIndex: 53, pointerEvents: 'none',
        alignItems: 'center',
      }}>
        {SEQUENCE.map((_, i) => {
          const isPast = i < beatIdx;
          const isCurrent = i === beatIdx;
          return (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
              <motion.span
                animate={{
                  width: isCurrent ? 22 : 5,
                  height: isCurrent ? 5 : 5,
                  background: isCurrent
                    ? 'rgba(255,230,190,0.95)'
                    : isPast
                    ? 'rgba(255,220,170,0.55)'
                    : 'rgba(255,255,255,0.22)',
                  boxShadow: isCurrent ? '0 0 10px rgba(255,220,170,0.7)' : '0 0 0 rgba(0,0,0,0)',
                }}
                transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
                style={{ borderRadius: 2, display: 'inline-block' }}
              />
              {i < SEQUENCE.length - 1 && (
                <span style={{ width: 8, height: 1, background: 'rgba(255,255,255,0.08)', display: 'inline-block' }} />
              )}
            </div>
          );
        })}
      </div>
    </motion.div>
  );
}

export default SpectrCubeIntro;
