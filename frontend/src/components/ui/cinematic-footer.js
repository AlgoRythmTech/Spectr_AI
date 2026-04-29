import React, { useRef } from 'react';
import { motion, useScroll, useTransform } from 'framer-motion';
import { Scale, ArrowUp, ChevronRight } from 'lucide-react';

/**
 * Cinematic Curtain-Reveal Footer for Spectr.
 * Adapted from GSAP/Tailwind to plain JS/inline styles + framer-motion for CRA.
 * The page content scrolls OVER this fixed footer, revealing it underneath.
 */

/* Magnetic button — follows cursor with spring physics */
function MagButton({ children, style = {}, onClick, href }) {
  const ref = useRef(null);
  const handleMove = (e) => {
    if (!ref.current) return;
    const r = ref.current.getBoundingClientRect();
    const x = (e.clientX - r.left - r.width / 2) * 0.3;
    const y = (e.clientY - r.top - r.height / 2) * 0.3;
    ref.current.style.transform = `translate(${x}px, ${y}px) scale(1.03)`;
  };
  const handleLeave = () => {
    if (ref.current) ref.current.style.transform = 'translate(0,0) scale(1)';
  };
  const Tag = href ? 'a' : 'div';
  return (
    <Tag ref={ref} href={href} onClick={onClick}
      onMouseMove={handleMove} onMouseLeave={handleLeave}
      style={{ transition: 'transform 0.5s cubic-bezier(0.16,1,0.3,1)', cursor: 'pointer', textDecoration: 'none', ...style }}>
      {children}
    </Tag>
  );
}

const MARQUEE_ITEMS = [
  'Deep Research', '✦', '185+ Legal Tools', '✦', '6-Tier AI Cascade', '✦',
  '50M+ Judgments', '✦', 'Blaxel Sandboxes', '✦', 'Zero Downtime', '✦',
  'SOC 2 Certified', '✦', 'E2E Encrypted', '✦',
];

const PILL_STYLE = {
  background: 'linear-gradient(145deg, rgba(10,10,10,0.06) 0%, rgba(10,10,10,0.02) 100%)',
  border: '1px solid rgba(10,10,10,0.08)',
  backdropFilter: 'blur(16px)',
  WebkitBackdropFilter: 'blur(16px)',
  boxShadow: '0 10px 30px -10px rgba(0,0,0,0.5), inset 0 1px 1px rgba(10,10,10,0.08), inset 0 -1px 2px rgba(0,0,0,0.3)',
  transition: 'all 0.4s cubic-bezier(0.16,1,0.3,1)',
};

const PILL_HOVER = (e) => {
  e.currentTarget.style.background = 'linear-gradient(145deg, rgba(10,10,10,0.1) 0%, rgba(10,10,10,0.04) 100%)';
  e.currentTarget.style.borderColor = 'rgba(10,10,10,0.15)';
  e.currentTarget.style.boxShadow = '0 20px 40px -10px rgba(0,0,0,0.6), inset 0 1px 1px rgba(10,10,10,0.15)';
};
const PILL_LEAVE = (e) => {
  e.currentTarget.style.background = PILL_STYLE.background;
  e.currentTarget.style.borderColor = 'rgba(10,10,10,0.08)';
  e.currentTarget.style.boxShadow = PILL_STYLE.boxShadow;
};

export function CinematicFooter({ onGetStarted }) {
  const wrapperRef = useRef(null);
  const { scrollYProgress } = useScroll({ target: wrapperRef, offset: ['start end', 'end end'] });
  const textY = useTransform(scrollYProgress, [0, 1], [80, 0]);
  const textOpacity = useTransform(scrollYProgress, [0, 0.5], [0, 1]);
  const bgScale = useTransform(scrollYProgress, [0, 1], [0.85, 1]);

  const scrollToTop = () => window.scrollTo({ top: 0, behavior: 'smooth' });

  return (
    <>
      <style>{`
        @keyframes cf-breathe{0%{transform:translate(-50%,-50%) scale(1);opacity:0.5}100%{transform:translate(-50%,-50%) scale(1.15);opacity:0.8}}
        @keyframes cf-marquee{from{transform:translateX(0)}to{transform:translateX(-50%)}}
        @keyframes cf-heartbeat{0%,100%{transform:scale(1)}15%,45%{transform:scale(1.25)}30%{transform:scale(1)}}
        .cf-grid{background-size:60px 60px;background-image:linear-gradient(to right,rgba(10,10,10,.03) 1px,transparent 1px),linear-gradient(to bottom,rgba(10,10,10,.03) 1px,transparent 1px);mask-image:linear-gradient(to bottom,transparent,black 30%,black 70%,transparent);-webkit-mask-image:linear-gradient(to bottom,transparent,black 30%,black 70%,transparent)}
      `}</style>

      {/* Curtain wrapper — clip-path reveals fixed footer underneath */}
      <div ref={wrapperRef} style={{ position: 'relative', height: '100vh', width: '100%', clipPath: 'polygon(0% 0, 100% 0%, 100% 100%, 0 100%)' }}>
        <footer style={{
          position: 'fixed', bottom: 0, left: 0, width: '100%', height: '100vh',
          display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
          overflow: 'hidden', background: '#fff', color: '#0A0A0A',
          fontFamily: "'Plus Jakarta Sans', sans-serif", WebkitFontSmoothing: 'antialiased',
        }}>

          {/* Aurora glow */}
          <div style={{
            position: 'absolute', left: '50%', top: '50%', width: '80vw', height: '60vh',
            borderRadius: '50%', pointerEvents: 'none', zIndex: 0,
            background: 'radial-gradient(circle, rgba(100,68,245,0.08) 0%, rgba(24,204,252,0.04) 40%, transparent 70%)',
            animation: 'cf-breathe 8s ease-in-out infinite alternate',
          }} />
          {/* Grid */}
          <div className="cf-grid" style={{ position: 'absolute', inset: 0, zIndex: 0, pointerEvents: 'none' }} />

          {/* Giant background text */}
          <motion.div style={{ scale: bgScale, opacity: textOpacity, position: 'absolute', bottom: '-5vh', left: '50%', transform: 'translateX(-50%)', whiteSpace: 'nowrap', zIndex: 0, pointerEvents: 'none', userSelect: 'none',
            fontSize: '22vw', lineHeight: 0.8, fontWeight: 900, letterSpacing: '-0.05em', color: 'transparent',
            WebkitTextStroke: '1px rgba(10,10,10,0.08)',
            background: 'linear-gradient(180deg, rgba(10,10,10,0.1) 0%, transparent 60%)',
            WebkitBackgroundClip: 'text', backgroundClip: 'text',
          }}>SPECTR</motion.div>

          {/* Marquee */}
          <div style={{ position: 'absolute', top: 48, left: 0, width: '100%', overflow: 'hidden', borderTop: '1px solid rgba(10,10,10,0.04)', borderBottom: '1px solid rgba(10,10,10,0.04)', background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(12px)', padding: '14px 0', zIndex: 10, transform: 'rotate(-1.5deg) scale(1.08)' }}>
            <div style={{ display: 'flex', width: 'max-content', animation: 'cf-marquee 35s linear infinite' }}>
              {[...MARQUEE_ITEMS, ...MARQUEE_ITEMS].map((item, i) => (
                <span key={i} style={{ fontSize: 11, fontWeight: 700, letterSpacing: '.2em', color: item === '✦' ? 'rgba(100,68,245,0.5)' : 'rgba(10,10,10,0.3)', textTransform: 'uppercase', padding: '0 16px', whiteSpace: 'nowrap' }}>{item}</span>
              ))}
            </div>
          </div>

          {/* Main content */}
          <motion.div style={{ y: textY, opacity: textOpacity, position: 'relative', zIndex: 10, flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '0 24px', marginTop: 80, maxWidth: 900, margin: '80px auto 0', width: '100%' }}>
            <h2 style={{
              fontFamily: "'Inter', sans-serif", fontSize: 'clamp(40px,8vw,80px)', fontWeight: 500,
              background: 'linear-gradient(180deg, #0A0A0A 0%, rgba(10,10,10,0.4) 100%)',
              WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
              letterSpacing: '-0.05em', marginBottom: 48, textAlign: 'center', lineHeight: 1,
              filter: 'drop-shadow(0 0 20px rgba(10,10,10,0.08))',
            }}>
              Ready to research smarter?
            </h2>

            {/* CTA pills */}
            <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: 16, marginBottom: 24 }}>
              <MagButton onClick={onGetStarted}>
                <div onMouseEnter={PILL_HOVER} onMouseLeave={PILL_LEAVE}
                  style={{ ...PILL_STYLE, background: '#0A0A0A', padding: '16px 36px', borderRadius: 999, display: 'flex', alignItems: 'center', gap: 10, fontSize: 15, fontWeight: 700, color: '#fff', border: '1px solid #0A0A0A' }}>
                  Get started free <ChevronRight style={{ width: 16, height: 16 }} />
                </div>
              </MagButton>
              <MagButton onClick={onGetStarted}>
                <div onMouseEnter={PILL_HOVER} onMouseLeave={PILL_LEAVE}
                  style={{ ...PILL_STYLE, padding: '16px 36px', borderRadius: 999, display: 'flex', alignItems: 'center', gap: 10, fontSize: 15, fontWeight: 600, color: 'rgba(10,10,10,0.6)' }}>
                  Request a demo
                </div>
              </MagButton>
            </div>

            {/* Link pills */}
            <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: 10, marginTop: 8 }}>
              {['Privacy Policy', 'Terms of Service', 'Security', 'Contact'].map(link => (
                <MagButton key={link}>
                  <div onMouseEnter={PILL_HOVER} onMouseLeave={PILL_LEAVE}
                    style={{ ...PILL_STYLE, padding: '10px 20px', borderRadius: 999, fontSize: 12, fontWeight: 600, color: 'rgba(10,10,10,0.35)' }}>
                    {link}
                  </div>
                </MagButton>
              ))}
            </div>
          </motion.div>

          {/* Bottom bar */}
          <div style={{ position: 'relative', zIndex: 20, width: '100%', padding: '0 32px 32px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16 }}>
            <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '.12em', color: 'rgba(10,10,10,0.2)', textTransform: 'uppercase' }}>
              &copy; 2025 Spectr Legal Technologies Pvt. Ltd.
            </div>

            <div onMouseEnter={PILL_HOVER} onMouseLeave={PILL_LEAVE}
              style={{ ...PILL_STYLE, padding: '10px 20px', borderRadius: 999, display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '.1em', color: 'rgba(10,10,10,0.3)', textTransform: 'uppercase' }}>Crafted with</span>
              <span style={{ animation: 'cf-heartbeat 2s ease-in-out infinite', color: '#ef4444', fontSize: 14 }}>❤</span>
              <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '.1em', color: 'rgba(10,10,10,0.3)', textTransform: 'uppercase' }}>in India</span>
            </div>

            <MagButton onClick={scrollToTop}>
              <div onMouseEnter={PILL_HOVER} onMouseLeave={PILL_LEAVE}
                style={{ ...PILL_STYLE, width: 44, height: 44, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'rgba(10,10,10,0.4)' }}>
                <ArrowUp style={{ width: 16, height: 16 }} />
              </div>
            </MagButton>
          </div>
        </footer>
      </div>
    </>
  );
}
