import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { 
  ArrowRight, BrainCircuit, ShieldCheck, Scale, FileSearch, Sparkles, 
  Terminal, Calculator, Database, FolderOpen, Lock, Activity, Layers, Server 
} from 'lucide-react';

/* ──────────────────────────────────────────────────────────────
   INTERSECTION OBSERVER HOOK FOR SMOOTH REVEALS
──────────────────────────────────────────────────────────────── */
function useScrollReveal() {
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
          }
        });
      },
      { threshold: 0.1, rootMargin: '0px 0px -50px 0px' }
    );

    document.querySelectorAll('.reveal-up, .reveal-blur, .reveal-scale, .reveal-left, .reveal-right').forEach((el) => {
      observer.observe(el);
    });

    return () => observer.disconnect();
  }, []);
}

/* ──────────────────────────────────────────────────────────────
   DATA
──────────────────────────────────────────────────────────────── */
const BENTO_FEATURES = [
  {
    icon: BrainCircuit,
    title: 'Multi-Model Synthesis',
    desc: 'Multiple advanced analysis engines deliberate your query simultaneously. Statutory, precedent, and risk are analyzed in parallel before a final synthesis delivers a definitive conclusion.',
    colSpan: 2,
  },
  {
    icon: Database,
    title: 'Statutory Grounding',
    desc: 'Deep integration with 18+ Central Acts ensuring no section number or clause is ever hallucinated.',
    colSpan: 1,
  },
  {
    icon: Scale,
    title: 'Court-Ready Submissions',
    desc: 'Draft Section 138 NI Act notices or bail applications with structural perfection and proper judicial formatting.',
    colSpan: 1,
  },
  {
    icon: Calculator,
    title: 'Deterministic Workflows',
    desc: 'From GSTR-2B 3-pass fuzzy reconciliation to automated TDS classification pipelines. We replaced probabilistic text generation with deterministic, auditor-grade computation engines.',
    colSpan: 2,
  },
];

const BOX_FEATURES = [
  { icon: FileSearch, title: 'Intelligent Entity Extraction', desc: 'Automatically extract PAN, GSTIN, and CIN numbers from uploaded tax notices and cross-verify their validity.' },
  { icon: Activity, title: 'Limitation Period Tracking', desc: 'Identify every date mentioned in a court order and instantly map the statutory timeline for appeals or replies.' },
  { icon: Layers, title: 'Cross-Document Reconciliation', desc: 'Upload a Bank Statement and a Ledger. Associate will probabilistically reconcile line items with 99.8% accuracy.' },
];

const MARQUEE_ITEMS = [
  'Tax Audit (Form 3CD)', 'GST SCN Rebuttal', '138 NI Act Notice', 'Bail Application', 
  'GSTR-2B Mapping', 'TDS Section 194 Classifier', 'Income Tax 143(1) Reply', 'FEMA Compounding',
  'IBC Section 9', 'Contract Review Matrix', 'Writ Petition Draft', 'Director Disqualification Check'
];

/* ──────────────────────────────────────────────────────────────
   MAIN
──────────────────────────────────────────────────────────────── */
export default function LandingPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  useScrollReveal();

  const go = () => navigate(user ? '/app/assistant' : '/login');

  return (
    <div style={{ minHeight: '100vh', position: 'relative', overflowX: 'hidden' }} data-testid="landing-page">
      
      {/* ── BACKGROUND AMBIENT ORBS ── */}
      <div className="ambient-orb orb-1" />
      <div className="ambient-orb orb-2" />

      {/* ── FLOATING NAV ── */}
      <div style={{ position: 'fixed', top: 20, left: 0, right: 0, zIndex: 100, display: 'flex', justifyContent: 'center', pointerEvents: 'none' }}>
        <nav className="nav-pill reveal-blur" style={{ pointerEvents: 'auto', display: 'flex', alignItems: 'center', padding: '6px 6px 6px 20px', gap: 32 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ width: 22, height: 22, background: '#000', borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Scale style={{ width: 12, height: 12, color: '#fff' }} />
            </div>
            <span style={{ fontSize: 15, fontWeight: 700, letterSpacing: '-0.02em', color: '#000' }}>Associate</span>
          </div>
          
          <div style={{ display: 'none', gap: 24, fontSize: 13, fontWeight: 500, color: '#4B5563', '@media (min-width: 768px)': { display: 'flex' } }}>
            <span style={{ cursor: 'pointer', transition: 'color 0.2s' }} onMouseEnter={e => e.currentTarget.style.color='#000'} onMouseLeave={e => e.currentTarget.style.color='#4B5563'}>Platform</span>
            <span style={{ cursor: 'pointer', transition: 'color 0.2s' }} onMouseEnter={e => e.currentTarget.style.color='#000'} onMouseLeave={e => e.currentTarget.style.color='#4B5563'}>Box</span>
            <span style={{ cursor: 'pointer', transition: 'color 0.2s' }} onMouseEnter={e => e.currentTarget.style.color='#000'} onMouseLeave={e => e.currentTarget.style.color='#4B5563'}>Security</span>
          </div>

          <button className="btn-premium" onClick={go} style={{ padding: '8px 18px', fontSize: 13 }}>
            {user ? 'Dashboard' : 'Get Access'}
          </button>
        </nav>
      </div>

      <main style={{ paddingTop: 180, paddingBottom: 120 }}>
        
        {/* ── 1. MACRO HERO ── */}
        <section style={{ textAlign: 'center', padding: '0 24px', marginBottom: 120 }}>
          <div className="reveal-blur delay-100" style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '6px 14px', background: 'rgba(0,0,0,0.03)', borderRadius: 100, border: '1px solid rgba(0,0,0,0.05)', fontSize: 12, fontWeight: 600, color: '#4B5563', marginBottom: 24 }}>
            <Sparkles style={{ width: 12, height: 12, color: '#000' }} />
            The Intelligence Engine for Indian Law & Tax
          </div>
          
          <h1 className="reveal-up delay-200 tracking-tightest text-balance" style={{ 
            fontSize: 'clamp(56px, 9vw, 110px)', 
            fontWeight: 600, 
            lineHeight: 1.02,
            color: '#000',
            maxWidth: 1200,
            margin: '0 auto 24px auto',
          }}>
            Reasoning, <span className="text-gradient">redefined.</span>
          </h1>
          
          <p className="reveal-up delay-300 text-balance" style={{
            fontSize: 'clamp(18px, 2.5vw, 26px)',
            color: '#4B5563',
            lineHeight: 1.5,
            maxWidth: 780,
            margin: '0 auto 48px auto',
            fontWeight: 400
          }}>
            Experience the world’s first multi-agent platform capable of drafting Supreme Court level submissions and orchestrating complex 3CD tax reconciliations.
          </p>

          <div className="reveal-up delay-400">
            <button className="btn-premium" onClick={go} style={{
              padding: '18px 40px', fontSize: 17, display: 'inline-flex', alignItems: 'center', gap: 10
            }}>
              Deploy Associate <ArrowRight style={{ width: 18, height: 18 }} />
            </button>
          </div>
        </section>

        {/* ── 2. FLOATING UI SHOWCASE ── */}
        <section style={{ padding: '0 24px', marginBottom: 180 }}>
          <div className="reveal-scale delay-500" style={{ maxWidth: 1100, margin: '0 auto' }}>
            <div className="hero-window">
              <div className="window-topbar">
                <div className="window-dot w-close" />
                <div className="window-dot w-min" />
                <div className="window-dot w-max" />
                <div style={{ margin: '0 auto', fontSize: 12, fontWeight: 500, color: '#9CA3AF', fontFamily: 'inherit' }}>
                  Associate — Indepth Synthesis
                </div>
              </div>
              
              <div style={{ display: 'flex', height: '640px', background: '#FAFAFA' }}>
                <div style={{ width: 260, borderRight: '1px solid rgba(0,0,0,0.04)', padding: 24, background: '#FFF' }}>
                  <div style={{ width: '80%', height: 12, background: '#F3F4F6', borderRadius: 4, marginBottom: 32 }} />
                  {[1,2,3,4,5,6].map(i => (
                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
                      <div style={{ width: 18, height: 18, borderRadius: 5, background: '#F3F4F6' }} />
                      <div style={{ width: '65%', height: 10, background: '#F3F4F6', borderRadius: 4 }} />
                    </div>
                  ))}
                </div>
                <div style={{ flex: 1, padding: 48, display: 'flex', flexDirection: 'column' }}>
                  <div style={{ alignSelf: 'flex-end', background: '#000', color: '#fff', padding: '16px 20px', borderRadius: '20px 20px 4px 20px', maxWidth: '70%', marginBottom: 32, fontSize: 15, lineHeight: 1.6 }}>
                    Draft a response to a GST SCN under S.74. The client mismatched ₹48L in ITC. Cite Supreme Court precedents regarding fraudulent intent vs sheer negligence.
                  </div>
                  
                  <div style={{ display: 'flex', gap: 16, marginBottom: 20 }}>
                    <div style={{ width: 32, height: 32, borderRadius: 8, background: '#000', display: 'flex', alignItems: 'center', justifyItems: 'center', flexShrink: 0 }}>
                      <Scale style={{ width: 16, height: 16, color: '#fff', margin: 'auto' }} />
                    </div>
                    <div style={{ background: '#FFF', border: '1px solid rgba(0,0,0,0.05)', borderRadius: '4px 20px 20px 20px', padding: '24px 32px', flex: 1, boxShadow: '0 4px 20px rgba(0,0,0,0.02)' }}>
                      <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
                        <span style={{ fontSize: 11, fontWeight: 600, padding: '4px 12px', background: '#EFF6FF', color: '#1E40AF', borderRadius: 100 }}>Statutory S.74</span>
                        <span style={{ fontSize: 11, fontWeight: 600, padding: '4px 12px', background: '#F5F3FF', color: '#6D28D9', borderRadius: 100 }}>IndianKanoon Search</span>
                      </div>
                      <div style={{ width: '100%', height: 12, background: '#F3F4F6', borderRadius: 4, marginBottom: 16 }} />
                      <div style={{ width: '90%', height: 12, background: '#F3F4F6', borderRadius: 4, marginBottom: 16 }} />
                      <div style={{ width: '60%', height: 12, background: '#F3F4F6', borderRadius: 4, marginBottom: 32 }} />
                      
                      <div style={{ borderLeft: '2px solid #000', paddingLeft: 20 }}>
                        <div style={{ width: '40%', height: 10, background: '#E5E7EB', borderRadius: 4, marginBottom: 12 }} />
                        <div style={{ width: '85%', height: 10, background: '#E5E7EB', borderRadius: 4 }} />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ── 3. WORKFLOW MARQUEE ── */}
        <section className="reveal-blur" style={{ padding: '40px 0', borderTop: '1px solid rgba(0,0,0,0.03)', borderBottom: '1px solid rgba(0,0,0,0.03)', marginBottom: 160, overflow: 'hidden', background: '#FFF' }}>
          <div className="animate-scroll-x" style={{ gap: 48, paddingLeft: 48 }}>
            {[...MARQUEE_ITEMS, ...MARQUEE_ITEMS].map((item, i) => (
              <span key={i} style={{ fontSize: 20, fontWeight: 500, color: '#9CA3AF', whiteSpace: 'nowrap' }}>{item}</span>
            ))}
          </div>
        </section>

        {/* ── 4. BENTO GRID ── */}
        <section style={{ maxWidth: 1100, margin: '0 auto', padding: '0 24px', marginBottom: 200 }}>
          <div className="reveal-up" style={{ textAlign: 'center', marginBottom: 80 }}>
            <div style={{ fontSize: 13, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: '#6B7280', marginBottom: 20 }}>The Ecosystem</div>
            <h2 className="tracking-tighter text-balance" style={{ fontSize: 'clamp(36px, 5vw, 56px)', fontWeight: 600, color: '#000', marginBottom: 20, lineHeight: 1.1 }}>
              A paradigm shift in legal operating systems.
            </h2>
            <p style={{ fontSize: 22, color: '#4B5563', maxWidth: 640, margin: '0 auto', lineHeight: 1.5 }}>
              We bypassed basic LLM wrappers to build deep, deterministic tooling engineered specifically for Indian professionals.
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 24, autoRows: 'minmax(300px, auto)' }}>
            {BENTO_FEATURES.map((feat, i) => (
              <div key={i} className={`bento-card reveal-up delay-${(i%3)*100}`} style={{ gridColumn: `span ${feat.colSpan}`, padding: 48, display: 'flex', flexDirection: 'column' }}>
                <div className="icon-wrap" style={{ marginBottom: 32 }}>
                  <feat.icon style={{ width: 24, height: 24, color: '#000' }} />
                </div>
                <h3 className="tracking-tighter" style={{ fontSize: 28, fontWeight: 600, color: '#000', marginBottom: 16 }}>{feat.title}</h3>
                <p style={{ fontSize: 18, color: '#6B7280', lineHeight: 1.6, margin: 0 }}>{feat.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* ── 5. THE BOX FEATURE ── */}
        <section style={{ maxWidth: 1100, margin: '0 auto', padding: '0 24px', marginBottom: 200 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 80, alignItems: 'center' }}>
            <div className="reveal-left">
              <div style={{ fontSize: 13, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: '#6B7280', marginBottom: 20 }}>The Box</div>
              <h2 className="tracking-tighter" style={{ fontSize: 'clamp(36px, 5vw, 56px)', fontWeight: 600, color: '#000', marginBottom: 24, lineHeight: 1.1 }}>
                A data room that reads documents like a senior attorney.
              </h2>
              <p style={{ fontSize: 20, color: '#4B5563', lineHeight: 1.6, marginBottom: 40 }}>
                Upload any PDF. Associate’s forensic extraction engine instantly breaks it down. We don't just search text — we parse tables, cross-verify computation math, and flag legal anomalies automatically.
              </p>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: 32 }}>
                {BOX_FEATURES.map((feat, i) => (
                  <div key={i} style={{ display: 'flex', gap: 16 }}>
                    <div style={{ width: 40, height: 40, borderRadius: 10, background: '#F3F4F6', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                      <feat.icon style={{ width: 18, height: 18, color: '#000' }} />
                    </div>
                    <div>
                      <h4 style={{ fontSize: 18, fontWeight: 600, color: '#000', marginBottom: 6 }}>{feat.title}</h4>
                      <p style={{ fontSize: 15, color: '#6B7280', lineHeight: 1.5, margin: 0 }}>{feat.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="reveal-right">
              {/* Box visually represented as an immense data pane */}
              <div className="bento-card" style={{ height: 600, background: 'linear-gradient(180deg, #FFFFFF 0%, #FAFAFA 100%)', display: 'flex', alignItems: 'center', justifyItems: 'center', padding: 40 }}>
                 <div style={{ width: '100%', border: '1px solid rgba(0,0,0,0.05)', borderRadius: 16, background: '#FFF', padding: 24, boxShadow: '0 10px 40px rgba(0,0,0,0.04)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 24, paddingBottom: 16, borderBottom: '1px solid #F3F4F6' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                        <FolderOpen style={{ width: 20, height: 20, color: '#000' }} />
                        <span style={{ fontWeight: 600, fontSize: 15 }}>TATA_Motors_SCN_Reply.pdf</span>
                      </div>
                      <span className="text-gradient" style={{ fontWeight: 600, fontSize: 13 }}>Forensic Extract</span>
                    </div>
                    
                    {[
                      { l: 'Demand Date', v: '14-Oct-2023', s: 'Verified' },
                      { l: 'Limitation End', v: '14-Nov-2023', s: 'At Risk' },
                      { l: 'Section Invoke', v: 'Section 74 (CGST)', s: 'Verified' },
                      { l: 'Total Mismatch', v: '₹48,12,044.00', s: 'Computed' }
                    ].map((item, i) => (
                      <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 0', borderBottom: i !== 3 ? '1px dashed #E5E7EB' : 'none' }}>
                        <span style={{ fontSize: 14, color: '#6B7280' }}>{item.l}</span>
                        <div style={{ textAlign: 'right' }}>
                          <div style={{ fontSize: 15, color: '#000', fontWeight: 500, fontFamily: 'IBM Plex Mono' }}>{item.v}</div>
                          <div style={{ fontSize: 11, color: item.s === 'At Risk' ? '#DC2626' : '#059669', fontWeight: 600, marginTop: 4 }}>{item.s.toUpperCase()}</div>
                        </div>
                      </div>
                    ))}
                 </div>
              </div>
            </div>
          </div>
        </section>

        {/* ── 6. SECURITY & COMPLIANCE (DARK MODE SECTION) ── */}
        <section style={{ padding: '0 24px', marginBottom: 200 }}>
          <div className="reveal-up" style={{ maxWidth: 1100, margin: '0 auto', background: '#000', borderRadius: 40, padding: '100px 64px', color: '#fff' }}>
             <div style={{ textAlign: 'center', marginBottom: 80 }}>
                <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 56, height: 56, borderRadius: 16, background: '#18181B', border: '1px solid rgba(255,255,255,0.1)', marginBottom: 24 }}>
                  <Lock style={{ width: 24, height: 24, color: '#FFF' }} />
                </div>
                <h2 className="tracking-tighter text-balance" style={{ fontSize: 'clamp(36px, 5vw, 56px)', fontWeight: 600, color: '#FFF', marginBottom: 20, lineHeight: 1.1 }}>
                  Bank-grade security.<br/><span className="text-gradient-dark">Zero data retention.</span>
                </h2>
                <p style={{ fontSize: 20, color: '#A1A1AA', maxWidth: 640, margin: '0 auto', lineHeight: 1.5 }}>
                  Configured meticulously for the stringent confidentiality requirements of India's elite law chambers and CA practices.
                </p>
             </div>

             <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 32 }}>
                {[
                  { icon: ShieldCheck, title: 'Zero Prompt Retention', desc: 'Queries, contexts, and uploaded documents are entirely ephemeral. No data is stored or used to train public LLM weights.' },
                  { icon: Server, title: 'Encrypted Enclaves', desc: 'All API communication occurs via AES-256 encrypted transit. Document parsing happens entirely in volatile memory.' },
                  { icon: Scale, title: 'Privilege Compliant', desc: 'Designed to strictly adhere to the Attorney-Client privilege mandate under the Indian Evidence Act, 1872.' }
                ].map((s, i) => (
                  <div key={i} className={`bento-card-dark reveal-up delay-${(i%3)*100}`} style={{ padding: 40 }}>
                    <div className="icon-wrap-dark" style={{ marginBottom: 24 }}>
                      <s.icon style={{ width: 20, height: 20, color: '#FFF' }} />
                    </div>
                    <h4 style={{ fontSize: 20, fontWeight: 600, color: '#FFF', marginBottom: 12 }}>{s.title}</h4>
                    <p style={{ fontSize: 16, color: '#A1A1AA', lineHeight: 1.6, margin: 0 }}>{s.desc}</p>
                  </div>
                ))}
             </div>
          </div>
        </section>

        {/* ── 7. DEEP DIVE METRICS ── */}
        <section className="reveal-up" style={{ padding: '0 24px', marginBottom: 200 }}>
          <div style={{ maxWidth: 1100, margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 64 }}>
            <div style={{ flex: '1 1 400px' }}>
              <h2 className="tracking-tighter text-balance" style={{ fontSize: 'clamp(36px, 5vw, 56px)', fontWeight: 600, marginBottom: 24, lineHeight: 1.1, color: '#000' }}>
                Intelligence that scales <br/><span className="text-gradient-subtle">with your practice.</span>
              </h2>
              <p style={{ fontSize: 22, color: '#6B7280', lineHeight: 1.5, margin: 0, maxWidth: 500 }}>
                Stop billing manual hours for classification and research. Let Associate compute the baseline while you focus on the advisory.
              </p>
            </div>
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 48 }}>
              <div>
                <div style={{ fontSize: 64, fontWeight: 500, letterSpacing: '-0.04em', color: '#000' }}>18<span style={{ color: '#9CA3AF' }}>+</span></div>
                <div style={{ fontSize: 16, fontWeight: 500, color: '#6B7280', marginTop: 4 }}>Central Acts Indexed</div>
              </div>
              <div>
                <div style={{ fontSize: 64, fontWeight: 500, letterSpacing: '-0.04em', color: '#000' }}>20<span style={{ color: '#9CA3AF' }}>+</span></div>
                <div style={{ fontSize: 16, fontWeight: 500, color: '#6B7280', marginTop: 4 }}>Automated Workflows</div>
              </div>
              <div>
                <div style={{ fontSize: 64, fontWeight: 500, letterSpacing: '-0.04em', color: '#000' }}>0</div>
                <div style={{ fontSize: 16, fontWeight: 500, color: '#6B7280', marginTop: 4 }}>Hallucinated Citations</div>
              </div>
              <div>
                <div style={{ fontSize: 64, fontWeight: 500, letterSpacing: '-0.04em', color: '#000' }}>99<span style={{ color: '#9CA3AF' }}>%</span></div>
                <div style={{ fontSize: 16, fontWeight: 500, color: '#6B7280', marginTop: 4 }}>Reconciliation Accuracy</div>
              </div>
            </div>
          </div>
        </section>

        {/* ── 8. BOTTOM CTA ── */}
        <section className="reveal-blur" style={{ textAlign: 'center', padding: '0 24px' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 80, height: 80, borderRadius: 24, background: '#000', marginBottom: 32, boxShadow: '0 12px 32px rgba(0,0,0,0.15)' }}>
            <Scale style={{ width: 40, height: 40, color: '#fff' }} />
          </div>
          <h2 className="tracking-tightest text-balance" style={{ fontSize: 'clamp(48px, 7vw, 80px)', fontWeight: 600, color: '#000', marginBottom: 24, lineHeight: 1.05 }}>
            Begin your firm's evolution.
          </h2>
          <p style={{ fontSize: 24, color: '#4B5563', marginBottom: 48 }}>
            Experience the reasoning engine built purely for Indian professionals.
          </p>
          <button className="btn-premium" onClick={go} style={{ padding: '20px 48px', fontSize: 20 }}>
            Get Started Now
          </button>
        </section>
      </main>

      <footer style={{ padding: '64px 48px', borderTop: '1px solid rgba(0,0,0,0.05)', display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr', gap: 48 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
            <div style={{ width: 28, height: 28, background: '#000', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Scale style={{ width: 14, height: 14, color: '#fff' }} />
            </div>
            <span style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.02em', color: '#000' }}>Associate</span>
          </div>
          <p style={{ fontSize: 15, color: '#6B7280', lineHeight: 1.6, maxWidth: 300 }}>
            The definitive AI platform for Indian legal and tax workflows.
          </p>
          <div style={{ marginTop: 40, fontSize: 13, color: '#9CA3AF' }}>
            © {new Date().getFullYear()} AlgoRythm Technologies. Made in India.
          </div>
        </div>
        
        <div>
          <h4 style={{ fontSize: 13, fontWeight: 700, color: '#000', marginBottom: 20, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Platform</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12, fontSize: 15, color: '#6B7280' }}>
            <span style={{ cursor: 'pointer' }}>Synthesis Engine</span>
            <span style={{ cursor: 'pointer' }}>Document Box</span>
            <span style={{ cursor: 'pointer' }}>GSTR-2B Reconciler</span>
            <span style={{ cursor: 'pointer' }}>Security</span>
          </div>
        </div>

        <div>
          <h4 style={{ fontSize: 13, fontWeight: 700, color: '#000', marginBottom: 20, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Resources</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12, fontSize: 15, color: '#6B7280' }}>
            <span style={{ cursor: 'pointer' }}>IndianKanoon Grounding</span>
            <span style={{ cursor: 'pointer' }}>Whitepaper</span>
            <span style={{ cursor: 'pointer' }}>API Documentation</span>
            <span style={{ cursor: 'pointer' }}>Help Center</span>
          </div>
        </div>

        <div>
          <h4 style={{ fontSize: 13, fontWeight: 700, color: '#000', marginBottom: 20, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Company</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12, fontSize: 15, color: '#6B7280' }}>
            <span style={{ cursor: 'pointer' }}>About Us</span>
            <span style={{ cursor: 'pointer' }}>Careers</span>
            <span style={{ cursor: 'pointer' }}>Privacy Policy</span>
            <span style={{ cursor: 'pointer' }}>Terms of Service</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
