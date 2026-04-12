import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  ArrowRight, Scale, CheckCircle,
  Shield, FileWarning, FileSpreadsheet, ArrowLeftRight,
  Calculator, Receipt, Upload
} from 'lucide-react';

/* ── Scroll reveal ── */
function useReveal() {
  useEffect(() => {
    const obs = new IntersectionObserver(
      (entries) => entries.forEach(e => {
        if (e.isIntersecting) {
          e.target.style.opacity = '1';
          e.target.style.transform = 'translateY(0) scale(1)';
          e.target.style.filter = 'blur(0)';
        }
      }),
      { threshold: 0.06, rootMargin: '0px 0px -80px 0px' }
    );
    document.querySelectorAll('[data-r]').forEach(el => obs.observe(el));
    return () => obs.disconnect();
  }, []);
}

/* ── Animated counter ── */
function Counter({ value, suffix = '' }) {
  const ref = useRef(null);
  const [display, setDisplay] = useState(value);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(([e]) => {
      if (!e.isIntersecting) return;
      const num = parseInt(value);
      if (isNaN(num)) { setDisplay(value); obs.disconnect(); return; }
      const start = performance.now();
      const dur = 1800;
      const step = (now) => {
        const p = Math.min((now - start) / dur, 1);
        const eased = 1 - Math.pow(1 - p, 4);
        setDisplay(Math.floor(num * eased) + suffix);
        if (p < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
      obs.disconnect();
    }, { threshold: 0.5 });
    obs.observe(el);
    return () => obs.disconnect();
  }, [value, suffix]);
  return <span ref={ref}>{display}</span>;
}

/* ── Reveal wrapper ── */
const R = ({ children, delay = 0, className = '', style = {}, ...props }) => (
  <div
    data-r
    className={className}
    style={{
      opacity: 0, transform: 'translateY(40px) scale(0.98)', filter: 'blur(6px)',
      transition: `all 0.9s cubic-bezier(0.16, 1, 0.3, 1) ${delay}ms`,
      willChange: 'opacity, transform, filter',
      ...style,
    }}
    {...props}
  >
    {children}
  </div>
);

const sans = "'Inter', -apple-system, BlinkMacSystemFont, sans-serif";

const CAPABILITIES = [
  { icon: FileWarning, title: 'GST Notice Auto-Reply', desc: 'Paste a Section 73/74 SCN. Get a 10-point legal reply with case law citations in 60 seconds.' },
  { icon: FileSpreadsheet, title: 'GSTR-2B Reconciliation', desc: '3-pass matching engine. Exact, fuzzy, and amount-based. Every ITC mismatch identified.' },
  { icon: ArrowLeftRight, title: 'IPC to BNS Mapper', desc: '120+ IPC sections mapped to BNS. 45+ CrPC to BNSS. Batch convert entire charge sheets.' },
  { icon: Receipt, title: 'TDS Classifier', desc: 'Describe the payment. Get the exact section, rate, threshold, and S.206AB non-filer risk.' },
  { icon: Calculator, title: 'Penalty Calculator', desc: 'Late GSTR-3B? Missed ITR? Exact late fee, interest, and total penalty with legal basis.' },
  { icon: Upload, title: 'Tally Import & Audit', desc: 'Upload Tally XML. Auto-detect S.40A(3) cash violations and S.269ST violations.' },
];

const TRUST = [
  'Every citation verified against IndianKanoon live API',
  'Updated for BNS/BNSS/BSA (effective July 1, 2024)',
  'Budget 2025-26 changes and AY 2026-27 slabs loaded',
  'Export to Word, Excel, and PDF instantly',
  'Bank-grade encryption, zero data retention',
  '5-tier AI model cascade for maximum accuracy',
];

export default function LandingPage() {
  const navigate = useNavigate();
  const { user, loading } = useAuth();
  useReveal();

  useEffect(() => {
    if (!loading && user) navigate('/app/assistant', { replace: true });
  }, [user, loading, navigate]);

  const go = () => navigate(user ? '/app/assistant' : '/login');

  return (
    <div style={{ minHeight: '100vh', fontFamily: sans, overflowX: 'hidden', background: '#0A0A0A' }}>

      {/* ─── NAV ─── */}
      <nav style={{
        position: 'fixed', top: 0, left: 0, right: 0, zIndex: 100,
        padding: '0 48px', height: 64,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        background: 'rgba(10,10,10,0.6)',
        backdropFilter: 'blur(24px) saturate(180%)',
        WebkitBackdropFilter: 'blur(24px) saturate(180%)',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 28, height: 28, background: '#fff', borderRadius: 8,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <Scale style={{ width: 14, height: 14, color: '#0A0A0A' }} />
          </div>
          <span style={{ fontSize: 17, fontWeight: 700, letterSpacing: '-0.03em', color: '#fff' }}>Associate</span>
        </div>
        <button onClick={go} style={{
          padding: '8px 22px', fontSize: 13, fontWeight: 600,
          background: '#fff', color: '#0A0A0A', border: 'none',
          borderRadius: 100, cursor: 'pointer',
          transition: 'all 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
        }}
        onMouseEnter={e => { e.currentTarget.style.transform = 'scale(1.04)'; e.currentTarget.style.boxShadow = '0 4px 20px rgba(255,255,255,0.15)'; }}
        onMouseLeave={e => { e.currentTarget.style.transform = 'scale(1)'; e.currentTarget.style.boxShadow = 'none'; }}
        >
          {user ? 'Open Dashboard' : 'Request Access'}
        </button>
      </nav>

      {/* ═══════════════════════════════════════════
          HERO — Dark, cinematic, massive type
          ═══════════════════════════════════════════ */}
      <section style={{
        position: 'relative', minHeight: '100vh',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        textAlign: 'center', padding: '0 32px', overflow: 'hidden',
      }}>
        {/* Animated gradient orbs */}
        <div style={{
          position: 'absolute', top: '-20%', left: '30%', width: 700, height: 700,
          borderRadius: '50%', filter: 'blur(120px)',
          background: 'radial-gradient(circle, rgba(255,255,255,0.06) 0%, transparent 70%)',
          animation: 'heroOrb1 12s ease-in-out infinite',
          pointerEvents: 'none',
        }} />
        <div style={{
          position: 'absolute', bottom: '-10%', right: '20%', width: 500, height: 500,
          borderRadius: '50%', filter: 'blur(100px)',
          background: 'radial-gradient(circle, rgba(255,255,255,0.04) 0%, transparent 70%)',
          animation: 'heroOrb2 15s ease-in-out infinite',
          pointerEvents: 'none',
        }} />

        {/* Grid pattern */}
        <div style={{
          position: 'absolute', inset: 0, opacity: 0.03,
          backgroundImage: `linear-gradient(rgba(255,255,255,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.5) 1px, transparent 1px)`,
          backgroundSize: '64px 64px',
          pointerEvents: 'none',
          maskImage: 'radial-gradient(ellipse at center, black 30%, transparent 70%)',
          WebkitMaskImage: 'radial-gradient(ellipse at center, black 30%, transparent 70%)',
        }} />

        <div style={{ position: 'relative', maxWidth: 900 }}>
          <R delay={100}>
            <div style={{
              display: 'inline-flex', alignItems: 'center', gap: 8,
              padding: '6px 16px 6px 12px', borderRadius: 100,
              background: 'rgba(255,255,255,0.06)',
              border: '1px solid rgba(255,255,255,0.08)',
              fontSize: 12, fontWeight: 600, color: 'rgba(255,255,255,0.5)',
              letterSpacing: '0.02em', marginBottom: 40,
            }}>
              <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#fff' }} />
              Built for Indian CAs and Lawyers
            </div>
          </R>

          <R delay={250}>
            <h1 style={{
              fontSize: 'clamp(52px, 8vw, 88px)',
              fontWeight: 700,
              lineHeight: 1.0,
              color: '#fff',
              letterSpacing: '-0.05em',
              margin: '0 0 28px',
            }}>
              Practice made<br />intelligent.
            </h1>
          </R>

          <R delay={400}>
            <p style={{
              fontSize: 'clamp(17px, 2.2vw, 21px)',
              color: 'rgba(255,255,255,0.4)',
              lineHeight: 1.6,
              maxWidth: 540,
              margin: '0 auto 48px',
              fontWeight: 400,
              letterSpacing: '-0.01em',
            }}>
              The AI platform that auto-replies to tax notices, reconciles GSTR-2B,
              maps IPC to BNS, and quantifies risk exposure — with every claim
              cited to its source.
            </p>
          </R>

          <R delay={550}>
            <div style={{ display: 'flex', gap: 14, justifyContent: 'center', flexWrap: 'wrap' }}>
              <button onClick={go} style={{
                padding: '16px 36px', fontSize: 15, fontWeight: 600,
                background: '#fff', color: '#0A0A0A', border: 'none',
                borderRadius: 100, cursor: 'pointer',
                display: 'inline-flex', alignItems: 'center', gap: 10,
                boxShadow: '0 0 40px rgba(255,255,255,0.08)',
                transition: 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
                fontFamily: sans,
              }}
              onMouseEnter={e => {
                e.currentTarget.style.transform = 'translateY(-2px) scale(1.03)';
                e.currentTarget.style.boxShadow = '0 0 60px rgba(255,255,255,0.15)';
              }}
              onMouseLeave={e => {
                e.currentTarget.style.transform = 'translateY(0) scale(1)';
                e.currentTarget.style.boxShadow = '0 0 40px rgba(255,255,255,0.08)';
              }}
              >
                Get Started <ArrowRight style={{ width: 16, height: 16 }} />
              </button>
              <button onClick={() => document.getElementById('capabilities')?.scrollIntoView({ behavior: 'smooth' })} style={{
                padding: '16px 32px', fontSize: 15, fontWeight: 600,
                color: 'rgba(255,255,255,0.6)', background: 'transparent',
                border: '1px solid rgba(255,255,255,0.12)', borderRadius: 100, cursor: 'pointer',
                transition: 'all 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
                fontFamily: sans,
              }}
              onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.06)'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.2)'; e.currentTarget.style.color = 'rgba(255,255,255,0.8)'; }}
              onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.12)'; e.currentTarget.style.color = 'rgba(255,255,255,0.6)'; }}
              >
                See Capabilities
              </button>
            </div>
          </R>

          {/* Scroll indicator */}
          <div style={{
            position: 'absolute', bottom: -80, left: '50%', transform: 'translateX(-50%)',
            display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8,
            animation: 'float 3s ease-in-out infinite',
          }}>
            <div style={{ width: 1, height: 32, background: 'linear-gradient(to bottom, rgba(255,255,255,0.2), transparent)' }} />
          </div>
        </div>
      </section>

      {/* ═══ METRICS — on dark ═══ */}
      <section style={{ borderTop: '1px solid rgba(255,255,255,0.06)', padding: '56px 0', background: '#0A0A0A' }}>
        <R>
          <div style={{
            maxWidth: 960, margin: '0 auto',
            display: 'flex', justifyContent: 'space-around', flexWrap: 'wrap', gap: 40,
            padding: '0 32px',
          }}>
            {[
              { num: '120', suffix: '+', label: 'Statute Sections' },
              { num: '17', suffix: '', label: 'TDS Sections' },
              { num: '3', suffix: '-Pass', label: 'Reconciliation' },
              { num: '60', suffix: 's', label: 'Notice Reply' },
            ].map((s, i) => (
              <div key={i} style={{ textAlign: 'center' }}>
                <div style={{
                  fontSize: 56, fontWeight: 700, letterSpacing: '-0.05em',
                  color: '#fff', lineHeight: 1,
                }}>
                  {s.num === '3' ? '3-Pass' : s.num === '60' ? '<' : ''}
                  <Counter value={s.num} suffix={s.suffix} />
                </div>
                <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.35)', fontWeight: 500, marginTop: 10 }}>
                  {s.label}
                </div>
              </div>
            ))}
          </div>
        </R>
      </section>

      {/* ═══ CAPABILITIES — white section ���══ */}
      <section id="capabilities" style={{ background: '#fff', padding: '120px 32px' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
          <R>
            <div style={{ textAlign: 'center', marginBottom: 72 }}>
              <h2 style={{
                fontSize: 'clamp(32px, 4vw, 52px)',
                fontWeight: 700, color: '#0A0A0A', marginBottom: 16,
                lineHeight: 1.08, letterSpacing: '-0.045em',
              }}>
                Purpose-built tools,<br />not generic AI chat.
              </h2>
              <p style={{ fontSize: 17, color: '#999', maxWidth: 480, margin: '0 auto', lineHeight: 1.55 }}>
                Every tool solves a specific problem CAs and lawyers face daily.
                Real data processing, not LLM summaries.
              </p>
            </div>
          </R>

          <div style={{
            display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 1,
            borderRadius: 24, overflow: 'hidden',
            background: 'rgba(0,0,0,0.04)',
          }}>
            {CAPABILITIES.map((feat, i) => (
              <R key={i} delay={i * 70} style={{
                padding: '44px 36px', background: '#fff',
                cursor: 'default',
                transition: 'background 0.3s ease',
              }}
              onMouseEnter={e => e.currentTarget.style.background = '#FAFAFA'}
              onMouseLeave={e => e.currentTarget.style.background = '#fff'}
              >
                <div style={{
                  width: 40, height: 40, borderRadius: 12,
                  background: '#F5F5F5', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  marginBottom: 20,
                }}>
                  <feat.icon style={{ width: 18, height: 18, color: '#0A0A0A', strokeWidth: 1.5 }} />
                </div>
                <h3 style={{
                  fontSize: 17, fontWeight: 650, color: '#0A0A0A',
                  marginBottom: 10, letterSpacing: '-0.02em',
                }}>{feat.title}</h3>
                <p style={{ fontSize: 14, color: '#888', lineHeight: 1.6, margin: 0 }}>{feat.desc}</p>
              </R>
            ))}
          </div>
        </div>
      </section>

      {/* ═══ CHAT DEMO — dark section ═══ */}
      <section style={{ background: '#0A0A0A', padding: '120px 32px' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 80, alignItems: 'center' }}>
          <R>
            <div style={{
              fontSize: 11, fontWeight: 600, letterSpacing: '0.12em',
              textTransform: 'uppercase', color: 'rgba(255,255,255,0.3)', marginBottom: 24,
            }}>
              AI Legal Assistant
            </div>
            <h2 style={{
              fontSize: 'clamp(28px, 3.5vw, 44px)',
              fontWeight: 700, color: '#fff', marginBottom: 24,
              lineHeight: 1.08, letterSpacing: '-0.04em',
            }}>
              Ask anything about Indian law and tax. Get cited answers.
            </h2>
            <p style={{ fontSize: 16, color: 'rgba(255,255,255,0.4)', lineHeight: 1.65, marginBottom: 40 }}>
              Deep reasoning engine backed by a verified statute database.
              Every section number, every case citation, every calculation
              is grounded — not hallucinated.
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {[
                'Quantifies risk exposure with exact rupee amounts',
                'Compares litigation strategies with success probabilities',
                'Traces multi-law cascades (GST + IT + Companies Act)',
                'Exports to Word, Excel, and PDF in one click',
              ].map((item, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 12, fontSize: 14, color: 'rgba(255,255,255,0.55)', lineHeight: 1.5 }}>
                  <CheckCircle style={{ width: 16, height: 16, color: 'rgba(255,255,255,0.3)', flexShrink: 0, marginTop: 2 }} />
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </R>

          <R delay={200}>
            <div style={{
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(255,255,255,0.08)',
              borderRadius: 20, overflow: 'hidden',
              boxShadow: '0 32px 80px -16px rgba(0,0,0,0.5)',
            }}>
              <div style={{
                height: 44, borderBottom: '1px solid rgba(255,255,255,0.06)',
                display: 'flex', alignItems: 'center', padding: '0 18px', gap: 7,
              }}>
                <div style={{ width: 10, height: 10, borderRadius: '50%', background: 'rgba(255,255,255,0.1)' }} />
                <div style={{ width: 10, height: 10, borderRadius: '50%', background: 'rgba(255,255,255,0.1)' }} />
                <div style={{ width: 10, height: 10, borderRadius: '50%', background: 'rgba(255,255,255,0.1)' }} />
                <span style={{ flex: 1, textAlign: 'center', fontSize: 11, color: 'rgba(255,255,255,0.25)', fontWeight: 600 }}>Associate</span>
              </div>
              <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 16 }}>
                <div style={{
                  background: 'rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.85)',
                  padding: '12px 16px', borderRadius: '16px 16px 4px 16px',
                  fontSize: 13, lineHeight: 1.55, alignSelf: 'flex-end', maxWidth: '82%',
                }}>
                  My client received a S.148A notice for AY 2019-20 without DIN. Grounds to challenge?
                </div>
                <div style={{
                  border: '1px solid rgba(255,255,255,0.06)', borderRadius: '16px 16px 16px 4px',
                  padding: 20, fontSize: 13, lineHeight: 1.65, color: 'rgba(255,255,255,0.6)',
                  background: 'rgba(255,255,255,0.02)',
                }}>
                  <div style={{ display: 'flex', gap: 6, marginBottom: 16 }}>
                    <span style={{ fontSize: 10, fontWeight: 700, padding: '3px 8px', background: 'rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.6)', borderRadius: 4 }}>S.148A Analysis</span>
                    <span style={{ fontSize: 10, fontWeight: 700, padding: '3px 8px', background: 'rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.6)', borderRadius: 4 }}>3 Grounds</span>
                  </div>
                  <p style={{ margin: '0 0 8px', fontWeight: 600, color: 'rgba(255,255,255,0.85)' }}>1. DIN Non-Compliance (Fatal)</p>
                  <p style={{ margin: '0 0 14px', color: 'rgba(255,255,255,0.4)', fontSize: 12.5 }}>
                    Per CBDT Circular 19/2019, every communication must bear a DIN. Absence renders void ab initio.
                    <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.2)', marginLeft: 4 }}>[Statute DB — verified]</span>
                  </p>
                  <p style={{ margin: '0 0 8px', fontWeight: 600, color: 'rgba(255,255,255,0.85)' }}>2. Limitation Period Expired</p>
                  <p style={{ margin: 0, color: 'rgba(255,255,255,0.4)', fontSize: 12.5 }}>
                    AY 2019-20, S.149(1)(a): reassessment only within 3 years from end of AY (31.03.2023)...
                  </p>
                </div>
              </div>
            </div>
          </R>
        </div>
      </section>

      {/* ═══ TRUST — white section ═══ */}
      <section style={{ background: '#fff', padding: '120px 32px' }}>
        <div style={{ maxWidth: 800, margin: '0 auto' }}>
          <R>
            <div style={{ textAlign: 'center', marginBottom: 56 }}>
              <div style={{
                display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                width: 48, height: 48, borderRadius: 14,
                background: '#F5F5F5', marginBottom: 24,
              }}>
                <Shield style={{ width: 20, height: 20, color: '#0A0A0A' }} />
              </div>
              <h2 style={{
                fontSize: 'clamp(28px, 4vw, 48px)',
                fontWeight: 700, color: '#0A0A0A', marginBottom: 16,
                lineHeight: 1.08, letterSpacing: '-0.045em',
              }}>
                Built for professionals who<br />cannot afford errors.
              </h2>
              <p style={{ fontSize: 17, color: '#999', maxWidth: 460, margin: '0 auto', lineHeight: 1.55 }}>
                Every output is grounded, cited, and verifiable.
                No hallucinated section numbers. No fabricated case names.
              </p>
            </div>
          </R>

          <R delay={100}>
            <div style={{
              display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
              gap: 8,
            }}>
              {TRUST.map((t, i) => (
                <div key={i} style={{
                  display: 'flex', alignItems: 'center', gap: 12,
                  padding: '14px 18px', borderRadius: 12,
                  background: '#FAFAFA',
                  transition: 'background 0.2s',
                }}
                onMouseEnter={e => e.currentTarget.style.background = '#F3F3F3'}
                onMouseLeave={e => e.currentTarget.style.background = '#FAFAFA'}
                >
                  <CheckCircle style={{ width: 15, height: 15, color: '#0A0A0A', flexShrink: 0 }} />
                  <span style={{ fontSize: 13, color: '#555' }}>{t}</span>
                </div>
              ))}
            </div>
          </R>
        </div>
      </section>

      {/* ═══ BOTTOM CTA — dark ═══ */}
      <section style={{
        background: '#0A0A0A', padding: '120px 32px', textAlign: 'center',
        position: 'relative', overflow: 'hidden',
      }}>
        <div style={{
          position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
          width: 600, height: 600, borderRadius: '50%', filter: 'blur(120px)',
          background: 'radial-gradient(circle, rgba(255,255,255,0.04) 0%, transparent 70%)',
          pointerEvents: 'none',
        }} />
        <R style={{ position: 'relative' }}>
          <h2 style={{
            fontSize: 'clamp(36px, 5vw, 68px)',
            fontWeight: 700, color: '#fff',
            marginBottom: 24, lineHeight: 1.02,
            letterSpacing: '-0.05em',
          }}>
            Your practice,<br />upgraded.
          </h2>
          <p style={{ fontSize: 18, color: 'rgba(255,255,255,0.35)', marginBottom: 44, maxWidth: 420, margin: '0 auto 44px' }}>
            Join CAs and lawyers who save hours every day.
          </p>
          <button onClick={go} style={{
            padding: '16px 44px', fontSize: 16, fontWeight: 600,
            background: '#fff', color: '#0A0A0A', border: 'none',
            borderRadius: 100, cursor: 'pointer', fontFamily: sans,
            boxShadow: '0 0 40px rgba(255,255,255,0.08)',
            transition: 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
          }}
          onMouseEnter={e => {
            e.currentTarget.style.transform = 'translateY(-2px) scale(1.03)';
            e.currentTarget.style.boxShadow = '0 0 60px rgba(255,255,255,0.15)';
          }}
          onMouseLeave={e => {
            e.currentTarget.style.transform = 'translateY(0) scale(1)';
            e.currentTarget.style.boxShadow = '0 0 40px rgba(255,255,255,0.08)';
          }}
          >
            Get Started Free
          </button>
        </R>
      </section>

      {/* ═══ FOOTER ═══ */}
      <footer style={{
        background: '#0A0A0A',
        borderTop: '1px solid rgba(255,255,255,0.06)',
        padding: '44px 48px 36px',
        display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 32,
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <div style={{ width: 22, height: 22, background: '#fff', borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Scale style={{ width: 11, height: 11, color: '#0A0A0A' }} />
            </div>
            <span style={{ fontSize: 15, fontWeight: 700, letterSpacing: '-0.03em', color: '#fff' }}>Associate</span>
          </div>
          <p style={{ fontSize: 13, color: 'rgba(255,255,255,0.3)', lineHeight: 1.5, maxWidth: 260 }}>
            AI-powered legal and tax intelligence for Indian professionals.
          </p>
          <div style={{ marginTop: 16, fontSize: 12, color: 'rgba(255,255,255,0.2)' }}>
            &copy; {new Date().getFullYear()} AlgoRythm Technologies. Made in India.
          </div>
        </div>
        <div style={{ display: 'flex', gap: 48 }}>
          <div>
            <h4 style={{ fontSize: 11, fontWeight: 700, color: 'rgba(255,255,255,0.5)', marginBottom: 14, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Tools</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, fontSize: 13, color: 'rgba(255,255,255,0.3)' }}>
              <span>GSTR-2B Reconciler</span>
              <span>Notice Auto-Reply</span>
              <span>IPC to BNS Mapper</span>
              <span>TDS Classifier</span>
            </div>
          </div>
          <div>
            <h4 style={{ fontSize: 11, fontWeight: 700, color: 'rgba(255,255,255,0.5)', marginBottom: 14, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Legal</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, fontSize: 13, color: 'rgba(255,255,255,0.3)' }}>
              <span>Privacy Policy</span>
              <span>Terms of Service</span>
              <span>Security</span>
            </div>
          </div>
        </div>
      </footer>

      {/* ─── CSS Animations ─── */}
      <style>{`
        @keyframes heroOrb1 {
          0%, 100% { transform: translate(0, 0) scale(1); }
          33% { transform: translate(60px, -40px) scale(1.1); }
          66% { transform: translate(-40px, 30px) scale(0.95); }
        }
        @keyframes heroOrb2 {
          0%, 100% { transform: translate(0, 0) scale(1); }
          50% { transform: translate(-50px, -30px) scale(1.15); }
        }
        @keyframes float {
          0%, 100% { transform: translateX(-50%) translateY(0); opacity: 0.4; }
          50% { transform: translateX(-50%) translateY(8px); opacity: 0.15; }
        }
      `}</style>
    </div>
  );
}
