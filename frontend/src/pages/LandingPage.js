import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence, useScroll, useTransform, useInView, useSpring, useMotionValue } from 'framer-motion';
import {
  Scale, FileSearch, Calculator, BrainCircuit, FolderOpen, ShieldCheck,
  CheckCircle2, ArrowRight, Lock, Database, Menu, X, Zap, Clock, Users,
  Globe, BookOpen, Sparkles, TrendingUp, Building2, Briefcase, Award,
  ChevronRight, ChevronDown, Layers, BarChart3, Target, Search, FileText, AlertTriangle,
  GitBranch, Calendar, Bell, Shield, Eye, Bot, Cpu, Network, FileCheck,
  GanttChart, Workflow, ArrowUpRight, Hash, Flame, BarChart, PieChart,
  Star,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { ContainerScroll } from '../components/ui/container-scroll';
import { AuroraBackground } from '../components/ui/aurora-background';
import { Spotlight } from '../components/ui/spotlight';
import { SpotlightFollow } from '../components/ui/spotlight-follow';
import { SmokeBackground } from '../components/ui/smoke-background';
import { GlassFilter, GlassButton } from '../components/ui/liquid-glass';
import { CanvasTrails } from '../components/ui/canvas-trails';
import { TextEffect } from '../components/ui/text-effect';
import { PulseBeams, CTA_BEAMS } from '../components/ui/pulse-beams';
import { BeamCanvas } from '../components/ui/beam-canvas';
import { SpectrAIDemo } from '../components/ui/spectr-ai-demo';
import { SpectrCubeIntro } from '../components/ui/spectr-cube-intro';
import { Typewriter } from '../components/ui/typewriter';
import { CinematicFooter } from '../components/ui/cinematic-footer';

/* ─── CONSTANTS ─── */
const EASE = [0.16, 1, 0.3, 1];
const HERO_WORDS = ['Research,', 'Intelligence,', 'Precision,', 'Spectr'];

const MARQUEE_ITEMS = [
  'Deep Research', 'Contract Redline', 'TDS Engine', 'GST Returns',
  'GSTR-2B Reconciliation', 'Due Diligence', 'Section Mapper', 'Notice Reply',
  'Penalty Calculator', 'ITR Computation', 'Case Law Search', 'Compliance Calendar',
  'Financial Analysis', 'Court Tracker', 'Document Vault', 'IBC/CIRP',
];

const STATS = [
  { value: 50, suffix: 'M+', label: 'Court judgments indexed', icon: BookOpen },
  { value: 185, suffix: '+', label: 'API tools & engines', icon: Zap },
  { value: 6, suffix: '-tier', label: 'AI model cascade', icon: BrainCircuit },
  { value: 8, suffix: '-step', label: 'Research pipeline', icon: Workflow },
];

const CAPABILITIES = [
  { icon: Scale, label: 'Deep Research', desc: '5-phase sandbox investigation with Blaxel VMs, opposing counsel analysis, and legislative timeline.' },
  { icon: FileSearch, label: 'Document AI', desc: 'Contract redline, clause extraction, risk scoring, and template matching in under 60 seconds.' },
  { icon: Calculator, label: 'Tax & GST Engine', desc: '15 TDS tools, 14 GST tools, ITR computation, GSTR-2B reconciliation, and DTAA rates.' },
  { icon: BrainCircuit, label: '6-Tier AI Cascade', desc: 'Gemini Pro → Flash → Lyzr → Claude → GPT-4o → Groq. Automatic failover, zero downtime.' },
  { icon: FolderOpen, label: 'Matter Vault', desc: 'RAG-powered document vault with version history, bulk upload, and AI Q&A over your files.' },
  { icon: ShieldCheck, label: '185+ Practice Tools', desc: 'Section mapper, penalty calculator, notice checker, stamp duty, forensic analysis, court tracking.' },
];

const FEATURE_DEEP_DIVES = [
  {
    label: 'Legal Research',
    icon: Scale,
    tagline: 'The core of legal intelligence',
    heading: 'Search 50 million judgments. Find the one that wins your case.',
    description: 'Spectr doesn\'t just search keywords — it understands legal intent. Our AI reads the full text of every Supreme Court, High Court, ITAT, NCLT, and Tribunal judgment ever published, then ranks results by relevance, citation strength, and jurisdictional authority. What used to take an associate 3 days now takes 3 minutes.',
    points: [
      { icon: Search, text: 'Semantic search that understands legal context, not just keywords' },
      { icon: BarChart3, text: 'Citation confidence scoring — know which judgments carry weight' },
      { icon: GitBranch, text: 'Precedent chain mapping — trace how case law evolved' },
      { icon: Target, text: 'Jurisdiction-aware filtering across all Indian courts and tribunals' },
    ],
    metrics: { value: '94%', label: 'research time reduction' },
    visual: 'search',
  },
  {
    label: 'Document AI',
    icon: FileSearch,
    tagline: 'Contracts, decoded in seconds',
    heading: 'Upload a contract. Get every risk flagged before you finish your coffee.',
    description: 'From 200-page M&A agreements to standard employment contracts, Spectr\'s Document AI reads every clause, identifies risks, flags non-standard terms, and generates redline suggestions — all in under 60 seconds. Multi-format support means PDFs, scanned documents, and DOCX files all work out of the box.',
    points: [
      { icon: FileText, text: 'Clause-level extraction — indemnity, termination, IP, liability, non-compete' },
      { icon: AlertTriangle, text: 'Risk scoring on a 1-10 scale with plain-English explanations' },
      { icon: Eye, text: 'Redline suggestions with tracked changes you can accept or reject' },
      { icon: FileCheck, text: 'Template matching — compare any contract against your firm\'s standards' },
    ],
    metrics: { value: '60s', label: 'average contract review' },
    visual: 'document',
  },
  {
    label: 'GST & Tax Compliance',
    icon: Calculator,
    tagline: 'Compliance, automated',
    heading: 'GSTR-2B reconciliation in one click. Not one weekend.',
    description: 'Every CA in India knows the pain — manually cross-referencing GSTR-2B data against purchase registers in Excel, row by row, GSTIN by GSTIN. Spectr eliminates this entirely. Upload your data or connect directly, and get a complete reconciliation report with ITC mismatches, vendor-wise breakdowns, and ready-to-file discrepancy summaries.',
    points: [
      { icon: BarChart, text: 'One-click GSTR-2B reconciliation across unlimited GSTINs' },
      { icon: AlertTriangle, text: 'ITC mismatch detection with vendor-level granularity' },
      { icon: FileText, text: 'Auto-drafted notices to non-compliant vendors with statutory references' },
      { icon: Calendar, text: 'Compliance calendar with proactive deadline alerts for every filing' },
    ],
    metrics: { value: '200+', label: 'hours saved per quarter' },
    visual: 'tax',
  },
  {
    label: 'AI Reasoning Engine',
    icon: BrainCircuit,
    tagline: 'Partner-level analysis, on demand',
    heading: 'Legal reasoning that thinks in chains, not keywords.',
    description: 'Spectr\'s reasoning engine doesn\'t just retrieve — it thinks. Trained specifically on Indian statutes including IPC, CPC, CrPC, CGST Act, Companies Act, SEBI regulations, and RBI circulars, it constructs multi-step reasoning chains that connect facts to law to precedent. Every conclusion is cited. Every citation is verified. Every argument considers counter-arguments.',
    points: [
      { icon: Cpu, text: 'Multi-step reasoning chains with transparent logic you can audit' },
      { icon: Network, text: 'Cross-statute analysis — connects provisions across IPC, CPC, CGST, and more' },
      { icon: Shield, text: 'Counter-argument identification — anticipate the other side\'s best case' },
      { icon: CheckCircle2, text: 'Every citation verified against source. Zero hallucination tolerance.' },
    ],
    metrics: { value: '99.2%', label: 'citation accuracy' },
    visual: 'reasoning',
  },
  {
    label: 'Matter Vault',
    icon: FolderOpen,
    tagline: 'Your firm\'s second brain',
    heading: 'Every matter, every document, every version — one secure vault.',
    description: 'Stop losing documents across email threads, shared drives, and WhatsApp groups. Matter Vault gives every engagement its own secure workspace with full version history, role-based access control, and intelligent tagging. Search across all matters instantly. Share with clients through secure portals. Maintain a complete audit trail for compliance.',
    points: [
      { icon: Layers, text: 'Per-matter workspaces with unlimited document storage and tagging' },
      { icon: GitBranch, text: 'Full version history — see every edit, by whom, and when' },
      { icon: Users, text: 'Role-based access control — associates, partners, and clients see only what they should' },
      { icon: GanttChart, text: 'Timeline tracking and milestone management for every engagement' },
    ],
    metrics: { value: '100%', label: 'audit trail coverage' },
    visual: 'vault',
  },
  {
    label: 'Compliance Engine',
    icon: ShieldCheck,
    tagline: 'Never miss a deadline again',
    heading: 'Regulatory changes happen daily. Spectr watches so you don\'t have to.',
    description: 'India\'s regulatory landscape changes constantly — new SEBI circulars, RBI master directions, MCA notifications, GST council decisions. Spectr\'s Compliance Engine monitors every gazette notification, every regulatory update, and every statutory change relevant to your practice areas and clients. You get jurisdiction-aware alerts before deadlines hit, not after.',
    points: [
      { icon: Bell, text: 'Real-time alerts for regulatory changes across SEBI, RBI, MCA, and GST' },
      { icon: Calendar, text: 'Smart compliance calendar — auto-populated based on your client portfolio' },
      { icon: Workflow, text: 'Filing tracker with status monitoring and escalation workflows' },
      { icon: Globe, text: 'Jurisdiction-aware — knows which regulations apply to which entity and state' },
    ],
    metrics: { value: '0', label: 'missed deadlines' },
    visual: 'compliance',
  },
];

const BEFORE_ITEMS = [
  'Manually sifting through 200+ cases on IndiaKanoon',
  'Copy-pasting citations into Word documents',
  'Cross-checking GSTR-2B with Excel sheets row by row',
  'Drafting notices from scratch every engagement',
  'Missing compliance deadlines under pressure',
  '3-5 days for a thorough legal research memo',
];

const AFTER_ITEMS = [
  'Instant ranked judgments with citation confidence scores',
  'Auto-formatted memos with verified citations built in',
  'One-click GSTR-2B reconciliation report in seconds',
  'AI-drafted notices with precedent references included',
  'Proactive deadline alerts and compliance calendar',
  'Comprehensive legal memo ready in under 3 minutes',
];

const INTEGRATIONS = [
  'Supreme Court of India', 'High Courts', 'ITAT', 'NCLT', 'NCLAT',
  'GST Portal', 'MCA', 'RBI', 'SEBI', 'IndiaKanoon',
  'SCC Online', 'Manupatra', 'Westlaw India', 'LexisNexis',
];

const SECURITY_CARDS = [
  { icon: ShieldCheck, label: 'SOC 2 Type II', desc: 'Enterprise-grade compliance with continuous monitoring and annual third-party audits.' },
  { icon: Lock, label: 'E2E Encrypted', desc: 'AES-256 encryption at rest and TLS 1.3 in transit. Your data is unreadable to anyone but you.' },
  { icon: Database, label: 'Data Isolation', desc: 'Per-client air-gapped storage with dedicated encryption keys and zero cross-tenant access.' },
];

/* ─── MOTION VARIANTS ─── */
const clipReveal = {
  hidden: { clipPath: 'inset(0 0 100% 0)' },
  visible: { clipPath: 'inset(0 0 0% 0)', transition: { duration: 1, ease: EASE } },
};
const fadeUp = {
  hidden: { opacity: 0, y: 40 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: EASE } },
};
const fadeIn = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: 0.8, ease: EASE } },
};
const scaleIn = {
  hidden: { opacity: 0, scale: 0.92 },
  visible: { opacity: 1, scale: 1, transition: { duration: 0.8, ease: EASE } },
};
const slideLeft = {
  hidden: { opacity: 0, x: -60 },
  visible: { opacity: 1, x: 0, transition: { duration: 0.8, ease: EASE } },
};
const slideRight = {
  hidden: { opacity: 0, x: 60 },
  visible: { opacity: 1, x: 0, transition: { duration: 0.8, ease: EASE } },
};
const cardUp = {
  hidden: { opacity: 0, y: 50, scale: 0.97 },
  visible: { opacity: 1, y: 0, scale: 1, transition: { duration: 0.7, ease: EASE } },
};
const listItem = {
  hidden: { opacity: 0, x: -20 },
  visible: { opacity: 1, x: 0, transition: { duration: 0.5, ease: EASE } },
};
const lineReveal = {
  hidden: { scaleX: 0 },
  visible: { scaleX: 1, transition: { duration: 1.2, ease: [0.22, 1, 0.36, 1] } },
};
const stagger = { hidden: {}, visible: { transition: { staggerChildren: 0.1 } } };
const staggerFast = { hidden: {}, visible: { transition: { staggerChildren: 0.06 } } };
const staggerSlow = { hidden: {}, visible: { transition: { staggerChildren: 0.15 } } };

/* ─── ENHANCED MOTION VARIANTS ─── */
const blurFadeUp = {
  hidden: { opacity: 0, y: 30, filter: 'blur(10px)' },
  visible: { opacity: 1, y: 0, filter: 'blur(0px)', transition: { duration: 0.9, ease: EASE } },
};
const rotateIn = {
  hidden: { opacity: 0, rotate: -5, scale: 0.9 },
  visible: { opacity: 1, rotate: 0, scale: 1, transition: { duration: 0.8, ease: EASE } },
};
const glowPulse = {
  animate: {
    boxShadow: [
      '0 0 20px rgba(10,10,10,0)',
      '0 0 40px rgba(10,10,10,0.06)',
      '0 0 20px rgba(10,10,10,0)',
    ],
    transition: { duration: 3, repeat: Infinity, ease: 'easeInOut' },
  },
};
const floatAnimation = {
  animate: {
    y: [0, -12, 0],
    transition: { duration: 4, repeat: Infinity, ease: 'easeInOut' },
  },
};

/* ─── FLOATING PARTICLES ─── */
function FloatingParticles({ count = 12, color = 'rgba(10,10,10,0.04)' }) {
  const particles = useRef(
    Array.from({ length: count }, () => ({
      left: Math.random() * 100,
      delay: Math.random() * 15,
      duration: 12 + Math.random() * 18,
      size: 2 + Math.random() * 3,
    }))
  ).current;
  return (
    <div style={{ position: 'absolute', inset: 0, overflow: 'hidden', pointerEvents: 'none', zIndex: 0 }}>
      {particles.map((p, i) => (
        <div key={i} style={{
          position: 'absolute', bottom: '-5%', left: `${p.left}%`,
          width: p.size, height: p.size, borderRadius: '50%', background: color,
          animation: `particleDrift ${p.duration}s ${p.delay}s linear infinite`,
        }} />
      ))}
    </div>
  );
}

/* ─── ORBITING DOT ─── */
function OrbitDot({ size = 4, radius = 40, duration = 8, color = 'rgba(100,68,245,0.5)', delay = 0 }) {
  return (
    <motion.div
      animate={{ rotate: 360 }}
      transition={{ duration, repeat: Infinity, ease: 'linear', delay }}
      style={{ position: 'absolute', width: radius * 2, height: radius * 2, top: '50%', left: '50%', marginTop: -radius, marginLeft: -radius }}
    >
      <div style={{ position: 'absolute', top: 0, left: '50%', marginLeft: -size / 2, width: size, height: size, borderRadius: '50%', background: color }} />
    </motion.div>
  );
}

/* ─── HOOKS ─── */
function useNavScroll() {
  const [s, setS] = useState(false);
  useEffect(() => {
    const h = () => setS(window.scrollY > 40);
    window.addEventListener('scroll', h, { passive: true });
    return () => window.removeEventListener('scroll', h);
  }, []);
  return s;
}

/* ─── 3D TILT CARD ─── Mouse-following perspective tilt */
function TiltCard({ children, style = {}, strength = 12, ...rest }) {
  const ref = useRef(null);
  const rx = useMotionValue(0);
  const ry = useMotionValue(0);
  const sx = useSpring(rx, { stiffness: 300, damping: 25 });
  const sy = useSpring(ry, { stiffness: 300, damping: 25 });
  const handleMove = (e) => {
    if (!ref.current) return;
    const r = ref.current.getBoundingClientRect();
    const px = (e.clientX - r.left) / r.width - 0.5;
    const py = (e.clientY - r.top) / r.height - 0.5;
    ry.set(px * strength);
    rx.set(-py * strength);
  };
  const handleLeave = () => { rx.set(0); ry.set(0); };
  return (
    <motion.div ref={ref} onMouseMove={handleMove} onMouseLeave={handleLeave}
      style={{ rotateX: sx, rotateY: sy, transformStyle: 'preserve-3d', perspective: 1000, ...style }}
      {...rest}>
      {children}
    </motion.div>
  );
}

/* ─── FLOATING 3D ICON ─── Icon that floats + rotates continuously */
function FloatingIcon3D({ children, delay = 0 }) {
  return (
    <motion.div
      animate={{ y: [0, -8, 0], rotateY: [0, 10, 0, -10, 0] }}
      transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut', delay }}
      style={{ transformStyle: 'preserve-3d', display: 'inline-block' }}
    >
      {children}
    </motion.div>
  );
}

/* ─── ANIMATED COUNTER ─── */
function Counter({ value, suffix = '', duration = 2 }) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: false, margin: '-100px' });
  const [count, setCount] = useState(0);
  useEffect(() => {
    if (!inView) return;
    let s = 0;
    const inc = value / (duration * 60);
    const t = setInterval(() => {
      s += inc;
      if (s >= value) { setCount(value); clearInterval(t); }
      else setCount(s);
    }, 1000 / 60);
    return () => clearInterval(t);
  }, [inView, value, duration]);
  const d = Number.isInteger(value) ? Math.floor(count) : count.toFixed(1);
  return <span ref={ref} style={{ fontVariantNumeric: 'tabular-nums' }}>{d}{suffix}</span>;
}

/* ─── MAGNETIC WRAP ─── */
function Mag({ children, strength = 0.3 }) {
  const ref = useRef(null);
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const sx = useSpring(x, { stiffness: 300, damping: 20 });
  const sy = useSpring(y, { stiffness: 300, damping: 20 });
  const move = (e) => {
    if (!ref.current) return;
    const r = ref.current.getBoundingClientRect();
    x.set((e.clientX - r.left - r.width / 2) * strength);
    y.set((e.clientY - r.top - r.height / 2) * strength);
  };
  const leave = () => { x.set(0); y.set(0); };
  return (
    <motion.div ref={ref} style={{ x: sx, y: sy, display: 'inline-block' }} onMouseMove={move} onMouseLeave={leave}>
      {children}
    </motion.div>
  );
}

/* ─── SECTION DIVIDER ─── */
function Divider() {
  return (
    <motion.div variants={lineReveal} initial="hidden" whileInView="visible" viewport={{ once: false, margin: '-20px' }}
      className="breathe"
      style={{ height: 1, background: 'linear-gradient(90deg, transparent, rgba(10,10,10,0.08), transparent)', transformOrigin: 'center', maxWidth: 1400, margin: '0 auto' }}
    />
  );
}

/* ─── FEATURE VISUAL MOCKUP ─── */
function FeatureVisual({ type }) {
  const base = {
    width: '100%', height: '100%', minHeight: 360, borderRadius: 24,
    background: 'rgba(10,10,10,0.02)', border: '1px solid rgba(10,10,10,0.06)',
    padding: 32, position: 'relative', overflow: 'hidden',
    fontFamily: "'JetBrains Mono', 'Inter', monospace",
  };
  const line = (w, op = 0.15) => ({
    height: 8, borderRadius: 4, marginBottom: 10,
    background: `rgba(10,10,10,${op})`, width: w,
  });
  const tag = (text) => (
    <span style={{
      display: 'inline-block', padding: '4px 10px', borderRadius: 6,
      background: 'rgba(10,10,10,0.05)', border: '1px solid rgba(10,10,10,0.08)',
      fontSize: 11, color: 'rgba(10,10,10,0.4)', marginRight: 6, marginBottom: 6,
    }}>{text}</span>
  );

  if (type === 'search') return (
    <div style={base}>
      <div style={{ fontSize: 11, color: 'rgba(10,10,10,0.3)', marginBottom: 16 }}>spectr &gt; research &gt; results</div>
      {['K.S. Puttaswamy v. Union of India', 'Maneka Gandhi v. Union of India', 'Gobind v. State of MP'].map((c, i) => (
        <motion.div key={c} initial={{ opacity: 0, x: -20 }} whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: false }} transition={{ delay: 0.2 + i * 0.15, duration: 0.5, ease: EASE }}
          style={{ padding: '14px 16px', borderRadius: 12, background: i === 0 ? 'rgba(10,10,10,0.05)' : 'transparent',
            border: '1px solid rgba(10,10,10,0.04)', marginBottom: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div style={{ fontSize: 13, color: i === 0 ? '#fff' : 'rgba(10,10,10,0.5)', fontWeight: 600, marginBottom: 4 }}>{c}</div>
            <div style={{ fontSize: 11, color: 'rgba(10,10,10,0.2)' }}>Supreme Court &middot; {2017 - i * 9} &middot; {9 - i * 2} bench</div>
          </div>
          <div style={{ padding: '4px 10px', borderRadius: 8, background: 'rgba(10,10,10,0.04)',
            fontSize: 12, color: 'rgba(10,10,10,0.5)', fontWeight: 600 }}>{98 - i * 5}%</div>
        </motion.div>
      ))}
      <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: 80,
        background: 'linear-gradient(transparent, rgba(0,0,0,0.8))', pointerEvents: 'none' }} />
    </div>
  );

  if (type === 'document') return (
    <div style={base}>
      <div style={{ fontSize: 11, color: 'rgba(10,10,10,0.3)', marginBottom: 16 }}>spectr &gt; document-ai &gt; review</div>
      <div style={{ display: 'flex', gap: 6, marginBottom: 16, flexWrap: 'wrap' }}>
        {tag('Indemnity')}{tag('Termination')}{tag('IP Rights')}{tag('Non-Compete')}{tag('Liability Cap')}
      </div>
      {[
        { clause: 'Section 8.2 — Indemnification', risk: 'High', color: '#ff4444' },
        { clause: 'Section 12.1 — Termination for Convenience', risk: 'Medium', color: '#ffaa00' },
        { clause: 'Section 15.3 — Limitation of Liability', risk: 'Low', color: '#44ff44' },
      ].map((c, i) => (
        <motion.div key={c.clause} initial={{ opacity: 0, y: 10 }} whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: false }} transition={{ delay: 0.3 + i * 0.12, duration: 0.5, ease: EASE }}
          style={{ padding: '12px 16px', borderRadius: 10, border: '1px solid rgba(10,10,10,0.04)',
            marginBottom: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            borderLeft: `3px solid ${c.color}20` }}>
          <span style={{ fontSize: 12, color: 'rgba(10,10,10,0.5)' }}>{c.clause}</span>
          <span style={{ fontSize: 10, padding: '3px 8px', borderRadius: 6, background: `${c.color}15`,
            color: c.color, fontWeight: 600 }}>{c.risk}</span>
        </motion.div>
      ))}
      <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: 60,
        background: 'linear-gradient(transparent, rgba(0,0,0,0.8))', pointerEvents: 'none' }} />
    </div>
  );

  if (type === 'tax') return (
    <div style={base}>
      <div style={{ fontSize: 11, color: 'rgba(10,10,10,0.3)', marginBottom: 16 }}>spectr &gt; gst &gt; reconciliation</div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginBottom: 20 }}>
        {[{ l: 'Matched', v: '₹4.2Cr', p: 87 }, { l: 'Mismatched', v: '₹48L', p: 10 }, { l: 'Missing', v: '₹14L', p: 3 }].map((s, i) => (
          <motion.div key={s.l} initial={{ opacity: 0, scale: 0.9 }} whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: false }} transition={{ delay: 0.2 + i * 0.1, duration: 0.5, ease: EASE }}
            style={{ padding: '16px 14px', borderRadius: 12, background: 'rgba(10,10,10,0.03)', border: '1px solid rgba(10,10,10,0.05)', textAlign: 'center' }}>
            <div style={{ fontSize: 20, fontWeight: 700, color: '#0A0A0A', fontFamily: "'Plus Jakarta Sans'" }}>{s.v}</div>
            <div style={{ fontSize: 10, color: 'rgba(10,10,10,0.3)', marginTop: 4 }}>{s.l} ({s.p}%)</div>
          </motion.div>
        ))}
      </div>
      <div style={line('100%', 0.06)} />
      <div style={line('87%', 0.12)} />
      <div style={line('10%', 0.08)} />
    </div>
  );

  if (type === 'reasoning') return (
    <div style={base}>
      <div style={{ fontSize: 11, color: 'rgba(10,10,10,0.3)', marginBottom: 16 }}>spectr &gt; reasoning &gt; chain</div>
      {['Identify applicable statutes (IPC §302, §304)', 'Retrieve relevant precedents (3 found)', 'Analyze factual matrix against ratio decidendi', 'Construct argument chain with citations'].map((step, i) => (
        <motion.div key={step} initial={{ opacity: 0, x: -16 }} whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: false }} transition={{ delay: 0.15 + i * 0.18, duration: 0.5, ease: EASE }}
          style={{ display: 'flex', gap: 12, alignItems: 'flex-start', marginBottom: 16 }}>
          <div style={{ width: 24, height: 24, borderRadius: 8, background: 'rgba(10,10,10,0.05)',
            border: '1px solid rgba(10,10,10,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 11, color: 'rgba(10,10,10,0.4)', flexShrink: 0, fontWeight: 700 }}>{i + 1}</div>
          <div>
            <div style={{ fontSize: 12, color: 'rgba(10,10,10,0.5)', lineHeight: 1.6 }}>{step}</div>
            {i < 3 && <div style={{ width: 1, height: 16, background: 'rgba(10,10,10,0.06)', marginLeft: 0, marginTop: 8 }} />}
          </div>
        </motion.div>
      ))}
    </div>
  );

  if (type === 'vault') return (
    <div style={base}>
      <div style={{ fontSize: 11, color: 'rgba(10,10,10,0.3)', marginBottom: 16 }}>spectr &gt; matters &gt; workspace</div>
      {[
        { name: 'Acme Corp — M&A Due Diligence', docs: 47, status: 'Active' },
        { name: 'TechStart — Series B Investment', docs: 23, status: 'Active' },
        { name: 'GlobalBank — RBI Compliance', docs: 156, status: 'Review' },
      ].map((m, i) => (
        <motion.div key={m.name} initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: false }} transition={{ delay: 0.2 + i * 0.12, duration: 0.5, ease: EASE }}
          style={{ padding: '14px 16px', borderRadius: 12, background: i === 0 ? 'rgba(10,10,10,0.04)' : 'transparent',
            border: '1px solid rgba(10,10,10,0.04)', marginBottom: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div style={{ fontSize: 13, color: 'rgba(10,10,10,0.6)', fontWeight: 500, marginBottom: 4, fontFamily: "'Plus Jakarta Sans'" }}>{m.name}</div>
            <div style={{ fontSize: 11, color: 'rgba(10,10,10,0.2)' }}>{m.docs} documents</div>
          </div>
          <span style={{ fontSize: 10, padding: '3px 8px', borderRadius: 6,
            background: 'rgba(10,10,10,0.04)', color: 'rgba(10,10,10,0.4)', fontWeight: 600 }}>{m.status}</span>
        </motion.div>
      ))}
    </div>
  );

  /* compliance */
  return (
    <div style={base}>
      <div style={{ fontSize: 11, color: 'rgba(10,10,10,0.3)', marginBottom: 16 }}>spectr &gt; compliance &gt; calendar</div>
      {[
        { date: 'Apr 20', task: 'GSTR-3B Filing — Maharashtra', urgent: true },
        { date: 'Apr 25', task: 'SEBI Quarterly Disclosure', urgent: false },
        { date: 'May 01', task: 'MCA Annual Return — Acme Corp', urgent: false },
        { date: 'May 15', task: 'RBI LRS Reporting Deadline', urgent: true },
      ].map((c, i) => (
        <motion.div key={c.task} initial={{ opacity: 0, x: -12 }} whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: false }} transition={{ delay: 0.15 + i * 0.1, duration: 0.5, ease: EASE }}
          style={{ display: 'flex', gap: 14, alignItems: 'center', padding: '10px 0',
            borderBottom: '1px solid rgba(10,10,10,0.03)' }}>
          <div style={{ width: 44, textAlign: 'center', fontSize: 11, color: 'rgba(10,10,10,0.3)', fontWeight: 600, flexShrink: 0 }}>{c.date}</div>
          <div style={{ flex: 1, fontSize: 12, color: 'rgba(10,10,10,0.5)' }}>{c.task}</div>
          {c.urgent && <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#ff4444', flexShrink: 0 }} />}
        </motion.div>
      ))}
    </div>
  );
}

/* ─── APP MOCKUP ─── */
function AppMockup() {
  return (
    <div style={{ display: 'flex', width: '100%', height: '100%', background: '#111', borderRadius: 12, overflow: 'hidden', fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
      <div style={{ width: 200, background: '#0A0A0A', padding: '20px 14px', borderRight: '1px solid rgba(10,10,10,0.06)', display: 'flex', flexDirection: 'column', gap: 4, flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', padding: '8px 10px', marginBottom: 16 }}>
          <span style={{ color: '#0A0A0A', fontSize: 16, fontWeight: 500, fontFamily: "'Inter', sans-serif", letterSpacing: '-0.05em' }}>Spectr</span>
        </div>
        {['Research', 'Documents', 'Compliance', 'Matters', 'Settings'].map((item, i) => (
          <div key={item} style={{ padding: '8px 10px', borderRadius: 8, fontSize: 13, color: i === 0 ? '#fff' : 'rgba(10,10,10,0.35)', background: i === 0 ? 'rgba(10,10,10,0.08)' : 'transparent', cursor: 'pointer', fontWeight: i === 0 ? 500 : 400 }}>{item}</div>
        ))}
      </div>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '14px 24px', borderBottom: '1px solid rgba(10,10,10,0.06)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ color: '#0A0A0A', fontSize: 14, fontWeight: 600 }}>Legal Research</span>
          <div style={{ padding: '4px 12px', background: 'rgba(10,10,10,0.06)', borderRadius: 6, fontSize: 11, color: 'rgba(10,10,10,0.4)' }}>AK</div>
        </div>
        <div style={{ flex: 1, padding: '24px 32px', overflow: 'hidden' }}>
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 20 }}>
            <div style={{ maxWidth: '70%', padding: '14px 18px', background: 'rgba(10,10,10,0.06)', borderRadius: '18px 18px 4px 18px', color: 'rgba(10,10,10,0.8)', fontSize: 13, lineHeight: 1.6 }}>
              What are the landmark Supreme Court judgments on Article 21 and the right to privacy?
            </div>
          </div>
          <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
            <div style={{ width: 28, height: 28, borderRadius: 8, background: '#0A0A0A', border: '1px solid rgba(10,10,10,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
              <Scale style={{ width: 12, height: 12, color: '#0A0A0A', strokeWidth: 2 }} />
            </div>
            <div>
              <div style={{ color: 'rgba(10,10,10,0.4)', fontSize: 11, marginBottom: 6, fontWeight: 600 }}>Spectr AI</div>
              <div style={{ color: 'rgba(10,10,10,0.7)', fontSize: 13, lineHeight: 1.7 }}>
                <strong style={{ color: '#0A0A0A' }}>K.S. Puttaswamy v. Union of India (2017)</strong> — The nine-judge bench unanimously held that the right to privacy is a fundamental right under Article 21...
              </div>
              <div style={{ marginTop: 10, display: 'inline-flex', gap: 6, padding: '4px 10px', background: 'rgba(10,10,10,0.04)', borderRadius: 6, color: 'rgba(10,10,10,0.3)', fontSize: 11 }}>
                <span style={{ color: 'rgba(10,10,10,0.5)' }}>3 citations</span> &middot; Supreme Court database
              </div>
            </div>
          </div>
        </div>
        <div style={{ padding: '12px 24px', borderTop: '1px solid rgba(10,10,10,0.06)' }}>
          <div style={{ padding: '10px 16px', background: 'rgba(10,10,10,0.04)', borderRadius: 12, border: '1px solid rgba(10,10,10,0.06)', color: 'rgba(10,10,10,0.2)', fontSize: 13 }}>Ask anything about Indian law...</div>
        </div>
      </div>
    </div>
  );
}


/* ─── SPLINE FRAME (scroll-safe) ─── */
function SplineFrame() {
  const [active, setActive] = useState(false);
  return (
    <div className="spline-frame" style={{ width: '100%', height: 560, borderRadius: 24, overflow: 'hidden', border: '1px solid rgba(10,10,10,.06)', boxShadow: '0 40px 120px rgba(0,0,0,.5)', position: 'relative' }}>
      <iframe
        src="https://my.spline.design/untitled-rv0hx3zVdoM6t2ydngxuS7zi/"
        style={{ width: '100%', height: '100%', border: 'none', pointerEvents: active ? 'auto' : 'none' }}
        title="Spectr 3D Experience"
        loading="lazy"
        allow="autoplay"
      />
      {!active && (
        <div
          onClick={() => setActive(true)}
          style={{
            position: 'absolute', inset: 0, zIndex: 2, cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: 'rgba(0,0,0,0.15)', transition: 'background .3s',
          }}
          onMouseEnter={e => e.currentTarget.style.background = 'rgba(0,0,0,0.05)'}
          onMouseLeave={e => e.currentTarget.style.background = 'rgba(0,0,0,0.15)'}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            style={{
              padding: '12px 24px', borderRadius: 16,
              background: 'rgba(10,10,10,0.06)', border: '1px solid rgba(10,10,10,0.1)',
              backdropFilter: 'blur(12px)',
              fontSize: 13, fontWeight: 600, color: 'rgba(10,10,10,0.6)',
              display: 'flex', alignItems: 'center', gap: 8,
            }}
          >
            <Sparkles style={{ width: 14, height: 14, strokeWidth: 1.5 }} />
            Click to interact
          </motion.div>
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════
   LANDING PAGE
   ═══════════════════════════════════════════════ */
export default function LandingPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const scrolled = useNavScroll();
  const [wordIdx, setWordIdx] = useState(0);
  const [mobileMenu, setMobileMenu] = useState(false);

  const heroRef = useRef(null);
  const { scrollYProgress: heroSP } = useScroll({ target: heroRef, offset: ['start start', 'end start'] });
  const heroOpacity = useTransform(heroSP, [0, 0.8], [1, 0]);
  const heroScale = useTransform(heroSP, [0, 0.8], [1, 0.96]);
  const heroY = useTransform(heroSP, [0, 1], [0, 100]);

  // Cinematic cube intro — shown once per session on first landing.
  // Two-phase state gives us a true crossfade: `introExiting` flips
  // ~520ms before `showIntro`, letting the landing fade IN while the
  // intro fades OUT in parallel (no sequential dead space).
  const [showIntro, setShowIntro] = useState(() => {
    if (typeof window === 'undefined') return false;
    return !sessionStorage.getItem('spectr_cube_intro_seen');
  });
  const [introExiting, setIntroExiting] = useState(false);
  const landingVisible = !showIntro || introExiting;
  const startIntroExit = useCallback(() => { setIntroExiting(true); }, []);
  const dismissIntro = useCallback(() => {
    setShowIntro(false);
    try { sessionStorage.setItem('spectr_cube_intro_seen', '1'); } catch { /* ignore */ }
  }, []);

  /* global scroll hooks removed — was causing scroll jank with blurred fixed elements */

  const go = useCallback(() => navigate(user ? '/app' : '/login'), [navigate, user]);

  useEffect(() => {
    const iv = setInterval(() => setWordIdx(i => (i + 1) % HERO_WORDS.length), 3000);
    return () => clearInterval(iv);
  }, []);

  const marquee2x = [...MARQUEE_ITEMS, ...MARQUEE_ITEMS];

  return (
    <>
    {showIntro && <SpectrCubeIntro onComplete={dismissIntro} onStartExit={startIntroExit} />}
    <div style={{
      fontFamily: "'Plus Jakarta Sans', system-ui, -apple-system, sans-serif",
      background: '#fff', color: '#0A0A0A', overflowX: 'hidden', WebkitFontSmoothing: 'antialiased',
      opacity: landingVisible ? 1 : 0,
      transform: landingVisible ? 'scale(1)' : 'scale(1.025)',
      filter: landingVisible ? 'blur(0)' : 'blur(10px)',
      transition: 'opacity 0.6s cubic-bezier(0.22, 1, 0.36, 1), transform 0.8s cubic-bezier(0.22, 1, 0.36, 1), filter 0.55s cubic-bezier(0.22, 1, 0.36, 1)',
      transformOrigin: '50% 45%',
    }}>
      <GlassFilter />

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,200..800;1,200..800&family=Outfit:wght@100..900&family=JetBrains+Mono:wght@400;500&display=swap');
        *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
        html{scroll-behavior:smooth;-webkit-overflow-scrolling:touch;scroll-padding-top:80px}
        body{-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;text-rendering:optimizeLegibility}
        *{-webkit-tap-highlight-color:transparent}
        ::selection{background:rgba(10,10,10,.15);color:#fff}
        @keyframes heroFade{from{opacity:0;transform:translateY(60px) scale(.97);filter:blur(8px)}to{opacity:1;transform:translateY(0) scale(1);filter:blur(0)}}
        @keyframes scrollLeft{from{transform:translateX(0)}to{transform:translateX(-50%)}}
        @keyframes scrollRight{from{transform:translateX(-50%)}to{transform:translateX(0)}}
        @keyframes pulse{0%,100%{opacity:.3}50%{opacity:1}}
        @keyframes gridFade{0%{opacity:.03}50%{opacity:.06}100%{opacity:.03}}
        .lp-nav{position:fixed;top:0;left:0;right:0;z-index:100;transition:background .5s cubic-bezier(.16,1,.3,1),backdrop-filter .5s,box-shadow .5s}
        .lp-nav.scrolled{background:rgba(255,255,255,.8);backdrop-filter:blur(24px) saturate(180%);-webkit-backdrop-filter:blur(24px) saturate(180%);border-bottom:1px solid rgba(10,10,10,.06);box-shadow:0 1px 40px rgba(0,0,0,.06)}
        .nav-link{font-size:14px;font-weight:500;color:rgba(10,10,10,.5);cursor:pointer;transition:color .25s;background:none;border:none;padding:6px 0;font-family:'Plus Jakarta Sans',sans-serif;letter-spacing:-.01em;position:relative}
        .nav-link::after{content:'';position:absolute;bottom:-2px;left:0;width:0;height:1px;background:#fff;transition:width .3s cubic-bezier(.16,1,.3,1)}
        .nav-link:hover{color:#fff}
        .nav-link:hover::after{width:100%}
        .nav-btn-get{display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:10px 22px;background:#0A0A0A;color:#fff;font-family:'Plus Jakarta Sans',sans-serif;font-size:14px;font-weight:600;border:none;border-radius:10px;cursor:pointer;letter-spacing:-.01em;transition:all .5s cubic-bezier(.16,1,.3,1);box-shadow:0 1px 2px rgba(0,0,0,.15),inset 0 1px 0 rgba(255,255,255,.1)}
        .nav-btn-get:hover{background:#1A1A1A;transform:translateY(-2px) scale(1.02);box-shadow:0 12px 40px rgba(0,0,0,.15),inset 0 1px 0 rgba(255,255,255,.15)}
        .nav-btn-get:active{transform:translateY(0) scale(0.97);transition:all .1s;box-shadow:inset 0 2px 4px rgba(0,0,0,.3)}
        .hero-btn-secondary{display:inline-flex;align-items:center;justify-content:center;gap:10px;padding:15px 28px;background:#fff;color:#0A0A0A;font-family:'Plus Jakarta Sans',sans-serif;font-size:16px;font-weight:500;border:1.5px solid rgba(10,10,10,.15);border-radius:16px;cursor:pointer;letter-spacing:-.01em;transition:all .5s cubic-bezier(.16,1,.3,1);box-shadow:0 1px 3px rgba(0,0,0,.04),inset 0 1px 0 rgba(255,255,255,.8)}
        .hero-btn-secondary:hover{border-color:#0A0A0A;color:#0A0A0A;transform:translateY(-3px) scale(1.02);box-shadow:0 12px 40px rgba(0,0,0,.08);background:#FAFAFA}
        .hero-btn-secondary:active{transform:translateY(0) scale(0.97);transition:all .1s;box-shadow:inset 0 2px 6px rgba(0,0,0,.06)}
        .cta-btn-primary{display:inline-flex;align-items:center;justify-content:center;gap:10px;padding:18px 36px;background:#0A0A0A;color:#fff;font-family:'Plus Jakarta Sans',sans-serif;font-size:16px;font-weight:600;border:none;border-radius:16px;cursor:pointer;letter-spacing:-.01em;transition:all .5s cubic-bezier(.16,1,.3,1);box-shadow:0 2px 4px rgba(0,0,0,.15),inset 0 1px 0 rgba(255,255,255,.1)}
        .cta-btn-primary:hover{background:#1A1A1A;transform:translateY(-4px) scale(1.02);box-shadow:0 24px 80px rgba(0,0,0,.18),inset 0 1px 0 rgba(255,255,255,.15)}
        .cta-btn-primary:active{transform:translateY(0) scale(0.97);transition:all .1s;box-shadow:inset 0 3px 6px rgba(0,0,0,.35)}
        .cta-btn-secondary{display:inline-flex;align-items:center;justify-content:center;gap:10px;padding:17px 28px;background:#fff;color:rgba(10,10,10,.7);font-family:'Plus Jakarta Sans',sans-serif;font-size:16px;font-weight:500;border:1.5px solid rgba(10,10,10,.12);border-radius:16px;cursor:pointer;transition:all .5s cubic-bezier(.16,1,.3,1);box-shadow:0 1px 3px rgba(0,0,0,.04),inset 0 1px 0 rgba(255,255,255,.8)}
        .cta-btn-secondary:hover{border-color:#0A0A0A;color:#0A0A0A;transform:translateY(-3px) scale(1.02);box-shadow:0 8px 32px rgba(0,0,0,.06);background:#FAFAFA}
        .cta-btn-secondary:active{transform:translateY(0) scale(0.97);transition:all .1s;box-shadow:inset 0 2px 6px rgba(0,0,0,.06)}
        .marquee-track{display:flex;width:max-content;animation:scrollLeft 24s linear infinite}
        .marquee-track:hover{animation-play-state:paused}
        .marquee-rev{display:flex;width:max-content;animation:scrollRight 28s linear infinite}
        .marquee-rev:hover{animation-play-state:paused}
        .mobile-menu-overlay{position:fixed;top:0;left:0;right:0;bottom:0;z-index:99;background:rgba(255,255,255,.98);backdrop-filter:blur(32px);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:32px}
        .mobile-menu-link{font-family:'Plus Jakarta Sans',sans-serif;font-size:28px;font-weight:700;color:rgba(10,10,10,.6);background:none;border:none;cursor:pointer;transition:color .3s}
        .mobile-menu-link:hover{color:#fff}
        .grid-bg{background-image:linear-gradient(rgba(10,10,10,.03) 1px,transparent 1px),linear-gradient(90deg,rgba(10,10,10,.03) 1px,transparent 1px);background-size:60px 60px;animation:gridFade 8s ease-in-out infinite}
        .noise{position:absolute;inset:0;z-index:0;pointer-events:none;opacity:.035;background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");background-repeat:repeat;background-size:256px 256px}
        @media(max-width:900px){
          .nav-desktop-links,.nav-desktop-right{display:none!important}
          .nav-mobile-btn{display:flex!important}
          .feat-grid,.sec-grid,.work-grid,.hiw-grid{grid-template-columns:1fr!important}
          .stats-grid{grid-template-columns:repeat(2,1fr)!important}
          .ba-wrap{flex-direction:column!important}
          .footer-links{flex-direction:column!important;align-items:flex-start!important;gap:16px!important}
          .scroll-section{display:none!important}
          .hero-buttons{flex-direction:column!important;align-items:center!important}
          .hero-buttons button{width:100%;max-width:320px}
          .dd-row{flex-direction:column!important}
          .dd-row-rev{flex-direction:column!important}
          .dd-visual{min-height:280px!important}
          .spline-frame{height:400px!important}
        }
        @media(max-width:600px){
          .hero-content-inner{padding:120px 20px 60px!important}
          .sp{padding-left:20px!important;padding-right:20px!important}
        }
        @keyframes shimmer{0%{background-position:-200% 0}100%{background-position:200% 0}}
        @keyframes borderGlow{0%,100%{border-color:rgba(10,10,10,.06)}50%{border-color:rgba(10,10,10,.12)}}
        @keyframes subtleFloat{0%,100%{transform:translateY(0)}50%{transform:translateY(-6px)}}
        @keyframes gradientShift{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}
        @keyframes dotPulse{0%,100%{box-shadow:0 0 0 0 rgba(34,197,94,0.4)}50%{box-shadow:0 0 0 6px rgba(34,197,94,0)}}
        .shimmer-text{background:linear-gradient(90deg,#fff 0%,rgba(10,10,10,.4) 50%,#fff 100%);background-size:200% 100%;-webkit-background-clip:text;-webkit-text-fill-color:transparent;animation:shimmer 3s linear infinite}
        .glow-border{animation:borderGlow 3s ease-in-out infinite}
        .gradient-text{background:linear-gradient(135deg,#fff 0%,rgba(10,10,10,.6) 50%,#fff 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
        .float-subtle{animation:subtleFloat 4s ease-in-out infinite}
        .gradient-shift{background-size:200% 200%;animation:gradientShift 6s ease infinite}
        .dot-pulse{animation:dotPulse 2s ease-in-out infinite}
        .card-hover{transition:all .5s cubic-bezier(.16,1,.3,1)}
        .card-hover:hover{transform:translateY(-6px);border-color:rgba(10,10,10,.12);box-shadow:0 24px 80px rgba(0,0,0,.3),0 0 0 1px rgba(10,10,10,.06)}
        @keyframes rotatingGradient{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}
        @keyframes particleDrift{0%{transform:translateY(0) translateX(0);opacity:0}10%{opacity:0.6}90%{opacity:0.6}100%{transform:translateY(-100vh) translateX(20px);opacity:0}}
        @keyframes orbOrbit{0%{transform:rotate(0deg) translateX(40px) rotate(0deg)}100%{transform:rotate(360deg) translateX(40px) rotate(-360deg)}}
        @keyframes textGlow{0%,100%{text-shadow:0 0 20px rgba(10,10,10,0)}50%{text-shadow:0 0 40px rgba(10,10,10,0.06)}}
        @keyframes lineExtend{0%{width:0}100%{width:100%}}
        @keyframes colorShift{0%{color:rgba(10,10,10,.5)}33%{color:rgba(100,68,245,.6)}66%{color:rgba(24,204,252,.6)}100%{color:rgba(10,10,10,.5)}}
        @keyframes borderRotate{0%{border-image-source:linear-gradient(0deg,rgba(10,10,10,.08),rgba(100,68,245,.15),rgba(10,10,10,.08))}100%{border-image-source:linear-gradient(360deg,rgba(10,10,10,.08),rgba(100,68,245,.15),rgba(10,10,10,.08))}}
        .text-glow{animation:textGlow 4s ease-in-out infinite}
        .color-shift{animation:colorShift 8s ease-in-out infinite}
        .rotating-gradient{background-size:200% 200%;animation:rotatingGradient 4s ease infinite}
        @keyframes breathe{0%,100%{opacity:.03}50%{opacity:.06}}
        @keyframes iconFloat{0%,100%{transform:translateY(0)}50%{transform:translateY(-4px)}}
        @keyframes borderBreath{0%,100%{border-color:rgba(10,10,10,.05)}50%{border-color:rgba(10,10,10,.1)}}
        @keyframes glowBreath{0%,100%{box-shadow:0 0 0 rgba(10,10,10,0)}50%{box-shadow:0 0 40px rgba(10,10,10,.03)}}
        @keyframes marqueeFloat{0%,100%{transform:translateY(0)}50%{transform:translateY(-2px)}}
        .breathe{animation:breathe 4s ease-in-out infinite}
        .icon-float{animation:iconFloat 3s ease-in-out infinite}
        .border-breathe{animation:borderBreath 4s ease-in-out infinite}
        .glow-breathe{animation:glowBreath 5s ease-in-out infinite}
        section{transition:opacity .6s cubic-bezier(.16,1,.3,1)}
        a,button,span[style*="cursor"]{transition:all .4s cubic-bezier(.16,1,.3,1)!important}
      `}</style>

      {/* Ambient glow — radial gradient only, NO blur filter on fixed elements (perf) */}
      <div style={{ position: 'fixed', top: '10%', left: '-12%', width: 700, height: 700, borderRadius: '50%', background: 'radial-gradient(circle,rgba(10,10,10,.015),transparent 60%)', pointerEvents: 'none', zIndex: 0 }} />
      <div style={{ position: 'fixed', bottom: '5%', right: '-15%', width: 800, height: 800, borderRadius: '50%', background: 'radial-gradient(circle,rgba(10,10,10,.01),transparent 55%)', pointerEvents: 'none', zIndex: 0 }} />

      {/* ═══ NAV ═══ */}
      <nav className={`lp-nav${scrolled ? ' scrolled' : ''}`}>
        <div style={{ maxWidth: 1400, margin: '0 auto', padding: '0 40px', height: 64, display: 'flex', alignItems: 'center', gap: 48 }}>
          <Mag strength={0.15}>
            <span onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })} style={{ fontFamily: "'Inter', sans-serif", fontSize: 22, fontWeight: 500, color: '#0A0A0A', cursor: 'pointer', letterSpacing: '-.05em', userSelect: 'none', background: 'linear-gradient(to bottom right, #0A0A0A 40%, rgba(10,10,10,0.5))', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}>
              Spectr
            </span>
          </Mag>
          <div className="nav-desktop-links" style={{ display: 'flex', alignItems: 'center', gap: 36, flex: 1 }}>
            {['Features', 'Research', 'Security', 'Pricing'].map(l => <button key={l} className="nav-link">{l}</button>)}
          </div>
          <div className="nav-desktop-right" style={{ display: 'flex', alignItems: 'center', gap: 16, marginLeft: 'auto' }}>
            <button className="nav-link" onClick={go}>{user ? 'Dashboard' : 'Sign in'}</button>
            <Mag strength={0.2}><button className="nav-btn-get" onClick={go}>Get started</button></Mag>
          </div>
          <button className="nav-mobile-btn" onClick={() => setMobileMenu(!mobileMenu)} style={{ display: 'none', marginLeft: 'auto', background: 'none', border: 'none', color: '#0A0A0A', cursor: 'pointer', padding: 8, alignItems: 'center', justifyContent: 'center' }}>
            {mobileMenu ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
      </nav>

      <AnimatePresence>
        {mobileMenu && (
          <motion.div className="mobile-menu-overlay" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.3 }}>
            <button onClick={() => setMobileMenu(false)} style={{ position: 'absolute', top: 20, right: 24, background: 'none', border: 'none', color: '#0A0A0A', cursor: 'pointer' }}><X size={28} /></button>
            {['Features', 'Research', 'Security', 'Pricing'].map((l, i) => (
              <motion.button key={l} className="mobile-menu-link" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.08, duration: 0.4, ease: EASE }} onClick={() => setMobileMenu(false)}>{l}</motion.button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {/* ═══ HERO ═══ */}
      <section ref={heroRef} style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative', overflow: 'hidden', background: '#fff' }}>
        <AuroraBackground style={{ zIndex: 0 }} showRadialGradient={true} />
        <BeamCanvas style={{ position: 'absolute', inset: 0, zIndex: 1, opacity: 0.2 }} beamCount={20} baseColor="rgba(10,10,10," />
        <Spotlight fill="black" style={{ position: 'absolute', top: '-40%', left: '-20%', width: '140%', height: '170%', zIndex: 1, opacity: 0.5 }} />
        <div style={{ position: 'absolute', inset: 0, zIndex: 2, background: 'radial-gradient(ellipse 80% 60% at 50% 40%,rgba(255,255,255,0) 0%,rgba(255,255,255,.35) 60%,rgba(255,255,255,.75) 100%)', pointerEvents: 'none' }} />
        <div className="noise" style={{ zIndex: 2 }} />

        <motion.div style={{ opacity: heroOpacity, scale: heroScale, y: heroY, maxWidth: 1000, margin: '0 auto', textAlign: 'center', padding: '160px 40px 100px', position: 'relative', zIndex: 3 }} className="hero-content-inner">
          <div style={{ animation: 'heroFade .8s cubic-bezier(.16,1,.3,1) 0s both' }}>
            <motion.span whileHover={{ scale: 1.05 }} className="glow-border" style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '8px 20px', background: 'rgba(10,10,10,.05)', border: '1px solid rgba(10,10,10,.08)', borderRadius: 999, fontSize: 13, fontWeight: 500, color: 'rgba(10,10,10,.45)', letterSpacing: '.02em', cursor: 'default', transition: 'border-color .3s', backdropFilter: 'blur(8px)' }}>
              <span className="dot-pulse" style={{ width: 6, height: 6, borderRadius: '50%', background: '#22c55e', display: 'inline-block' }} />
              Backed by 185+ AI-powered legal tools
            </motion.span>
          </div>

          <div style={{ animation: 'heroFade .9s cubic-bezier(.16,1,.3,1) .1s both', marginTop: 40, minHeight: 'clamp(72px,10vw,120px)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <AnimatePresence mode="wait">
              <motion.span key={HERO_WORDS[wordIdx]} initial={{ opacity: 0, y: 30, filter: 'blur(12px)' }} animate={{ opacity: 1, y: 0, filter: 'blur(0)' }} exit={{ opacity: 0, y: -30, filter: 'blur(12px)' }} transition={{ duration: 0.6, ease: EASE }}
                style={{ fontFamily: "'Inter',sans-serif", fontSize: 'clamp(64px,9.5vw,112px)', fontWeight: 500, background: 'linear-gradient(to bottom right, #0A0A0A 40%, rgba(10,10,10,0.55))', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', letterSpacing: '-.05em', lineHeight: 1, display: 'block' }}>{HERO_WORDS[wordIdx]}</motion.span>
            </AnimatePresence>
          </div>

          <div style={{ animation: 'heroFade .9s cubic-bezier(.16,1,.3,1) .15s both' }}>
            <span style={{ fontFamily: "'Inter',sans-serif", fontSize: 'clamp(64px,9.5vw,112px)', fontWeight: 500, background: 'linear-gradient(to bottom right, rgba(10,10,10,0.55) 30%, rgba(10,10,10,0.25))', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', letterSpacing: '-.05em', lineHeight: 1 }}>Redefined.</span>
          </div>

          <div style={{ animation: 'heroFade .9s cubic-bezier(.16,1,.3,1) .2s both', maxWidth: 560, margin: '36px auto 0' }}>
            <TextEffect
              per="word"
              preset="blur"
              delay={0.4}
              as="p"
              style={{ fontSize: 'clamp(17px,2vw,21px)', color: 'rgba(10,10,10,.4)', lineHeight: 1.65, letterSpacing: '-.01em', margin: 0 }}
            >
              The AI legal platform that researches 50M+ judgments, drafts with citations, and files with zero errors — so your team can focus on high-value work.
            </TextEffect>
          </div>

          {/* Typewriter capability showcase */}
          <div style={{ animation: 'heroFade .9s cubic-bezier(.16,1,.3,1) .25s both', marginTop: 28, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
            <span style={{ fontSize: 15, color: 'rgba(10,10,10,.25)', fontFamily: "'JetBrains Mono', monospace" }}>spectr</span>
            <span style={{ fontSize: 15, color: 'rgba(10,10,10,.12)', fontFamily: "'JetBrains Mono', monospace" }}>/</span>
            <Typewriter
              text={[
                'deep research with sandbox VMs',
                'redline contracts in 60 seconds',
                'reconcile GSTR-2B in one click',
                'compute TDS across all sections',
                'track 185+ compliance deadlines',
                '6-tier AI cascade, zero downtime',
                'draft notice replies with citations',
                'map IPC sections to new BNS codes',
              ]}
              speed={45}
              deleteSpeed={25}
              waitTime={2200}
              loop={true}
              initialDelay={1500}
              cursorChar="_"
              style={{ fontSize: 15, color: 'rgba(10,10,10,.5)', fontFamily: "'JetBrains Mono', monospace" }}
              cursorStyle={{ color: 'rgba(10,10,10,.3)' }}
            />
          </div>

          <div className="hero-buttons" style={{ animation: 'heroFade .9s cubic-bezier(.16,1,.3,1) .3s both', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 16, marginTop: 48, flexWrap: 'wrap' }}>
            <Mag strength={0.25}>
              <GlassButton onClick={go} style={{ borderRadius: 16 }} data-cursor="Launch">
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 10, fontSize: 16, fontWeight: 600, color: '#0A0A0A', letterSpacing: '-.01em' }}>
                  Start for free <motion.span animate={{ x: [0, 4, 0] }} transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}><ArrowRight style={{ width: 16, height: 16 }} /></motion.span>
                </span>
              </GlassButton>
            </Mag>
            <Mag strength={0.25}><button className="hero-btn-secondary" onClick={go} data-cursor="Demo">Request a demo</button></Mag>
          </div>

          <p style={{ animation: 'heroFade .9s cubic-bezier(.16,1,.3,1) .4s both', fontSize: 13, color: 'rgba(10,10,10,.2)', marginTop: 20, letterSpacing: '.01em' }}>No credit card required</p>

          {/* Trust strip — YC-level social proof */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1.2, duration: 0.8, ease: EASE }}
            style={{ marginTop: 64, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 }}
          >
            <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: '.12em', color: 'rgba(10,10,10,.15)', textTransform: 'uppercase' }}>Trusted by teams at</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 32, flexWrap: 'wrap', justifyContent: 'center' }}>
              {['Cyril Amarchand', 'AZB & Partners', 'Shardul Amarchand', 'Khaitan & Co', 'Trilegal'].map((name, i) => (
                <motion.span key={name}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 1.4 + i * 0.1, duration: 0.5 }}
                  style={{ fontSize: 13, fontWeight: 500, color: 'rgba(10,10,10,.18)', letterSpacing: '-.01em', fontFamily: "'Plus Jakarta Sans', sans-serif" }}
                >{name}</motion.span>
              ))}
            </div>
          </motion.div>
        </motion.div>

        {/* Scroll indicator */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 2, duration: 1 }}
          style={{ position: 'absolute', bottom: 40, left: '50%', transform: 'translateX(-50%)', zIndex: 5, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}
        >
          <span style={{ fontSize: 10, fontWeight: 600, letterSpacing: '.1em', color: 'rgba(10,10,10,.15)', textTransform: 'uppercase' }}>Scroll</span>
          <motion.div
            animate={{ y: [0, 8, 0], opacity: [0.2, 0.5, 0.2] }}
            transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
            style={{ width: 1, height: 24, background: 'linear-gradient(to bottom, rgba(10,10,10,0.3), transparent)' }}
          />
        </motion.div>

        <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: 200, background: 'linear-gradient(to bottom,transparent,#000)', zIndex: 4, pointerEvents: 'none' }} />
      </section>

      {/* ═══ MARQUEE ═══ */}
      <section style={{ background: '#fff', overflow: 'hidden', borderTop: '1px solid rgba(10,10,10,.04)', borderBottom: '1px solid rgba(10,10,10,.04)', padding: '28px 0' }}>
        <div className="marquee-track">
          {marquee2x.map((item, i) => (
            <span key={`${item}-${i}`} style={{ fontFamily: "'Plus Jakarta Sans',sans-serif", fontStyle: 'italic', fontSize: 24, color: 'rgba(10,10,10,.1)', whiteSpace: 'nowrap', padding: '0 24px', letterSpacing: '-.01em', display: 'inline-flex', alignItems: 'center', gap: 24 }}>
              {item}<span style={{ fontSize: 8, color: 'rgba(10,10,10,.06)' }}>&#9670;</span>
            </span>
          ))}
        </div>
      </section>

      {/* ═══ PRODUCT SHOWCASE ═══ */}
      <section className="scroll-section" style={{ background: '#fff' }}>
        <ContainerScroll titleComponent={
          <div style={{ textAlign: 'center' }}>
            <motion.div variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: false, margin: '-80px' }}
              style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '7px 16px', background: 'rgba(10,10,10,.04)', border: '1px solid rgba(10,10,10,.08)', borderRadius: 999, fontSize: 12, fontWeight: 600, color: 'rgba(10,10,10,.35)', letterSpacing: '.04em', textTransform: 'uppercase', marginBottom: 24 }}>
              <span className="dot-pulse" style={{ width: 5, height: 5, borderRadius: '50%', background: '#22c55e' }} />
              Live Product
            </motion.div>
            <motion.h2 variants={clipReveal} initial="hidden" whileInView="visible" viewport={{ once: false, margin: '-80px' }}
              style={{ fontFamily: "'Inter',sans-serif", fontSize: 'clamp(32px,5vw,56px)', fontWeight: 500, background: 'linear-gradient(to bottom right, #0A0A0A 40%, rgba(10,10,10,0.45))', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', letterSpacing: '-.05em', lineHeight: 1.1, maxWidth: 700, margin: '0 auto' }}>
              One platform. 185+ tools. Zero context switching.
            </motion.h2>
            <motion.p variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: false, margin: '-60px' }}
              style={{ fontSize: 16, color: 'rgba(10,10,10,.3)', maxWidth: 480, margin: '16px auto 0', lineHeight: 1.7 }}>
              Research, draft, reconcile, and file — all from a single intelligent interface that understands Indian law.
            </motion.p>
          </div>
        }><AppMockup /></ContainerScroll>
      </section>

      <Divider />

      {/* ═══ STATS ═══ */}
      <section style={{ background: '#fff', padding: '120px 40px', position: 'relative', overflow: 'hidden' }} className="sp">
        <div className="noise" />
        <FloatingParticles count={8} color="rgba(10,10,10,0.025)" />
        {/* Moving gradient blob behind */}
        <motion.div
          animate={{ x: [-100, 100, -100], y: [0, -50, 0] }}
          transition={{ duration: 20, repeat: Infinity, ease: 'easeInOut' }}
          style={{ position: 'absolute', top: '30%', left: '20%', width: 400, height: 400, borderRadius: '50%', background: 'radial-gradient(circle, rgba(100,68,245,0.04) 0%, transparent 70%)', filter: 'blur(60px)', pointerEvents: 'none', zIndex: 0 }}
        />
        <motion.div
          animate={{ x: [100, -100, 100], y: [0, 50, 0] }}
          transition={{ duration: 25, repeat: Infinity, ease: 'easeInOut', delay: 5 }}
          style={{ position: 'absolute', bottom: '20%', right: '15%', width: 500, height: 500, borderRadius: '50%', background: 'radial-gradient(circle, rgba(24,204,252,0.03) 0%, transparent 70%)', filter: 'blur(80px)', pointerEvents: 'none', zIndex: 0 }}
        />
        <div style={{ maxWidth: 1200, margin: '0 auto', position: 'relative', zIndex: 1 }}>
          <motion.div className="stats-grid" variants={stagger} initial="hidden" whileInView="visible" viewport={{ once: false, margin: '-80px' }}
            style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 32 }}>
            {STATS.map((s, i) => {
              const Icon = s.icon;
              return (
                <TiltCard key={s.label} strength={10} style={{ height: '100%' }}>
                <motion.div variants={cardUp} whileHover={{ y: -8, borderColor: 'rgba(10,10,10,.14)', boxShadow: '0 32px 80px rgba(10,10,10,0.08)' }}
                  className="border-breathe"
                  style={{ textAlign: 'center', padding: '48px 24px', background: '#fff', border: '1px solid rgba(10,10,10,.06)', borderRadius: 24, transition: 'all .5s cubic-bezier(.16,1,.3,1)', position: 'relative', overflow: 'hidden', transformStyle: 'preserve-3d' }}>
                  <motion.div initial={{ scale: 0, opacity: 0 }} whileInView={{ scale: 1, opacity: 1 }} viewport={{ once: false }} transition={{ delay: i * 0.1 + 0.2, duration: 0.6, ease: EASE }}
                    className="icon-float" style={{ width: 48, height: 48, borderRadius: 14, background: 'rgba(10,10,10,.04)', border: '1px solid rgba(10,10,10,.06)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 24px', animationDelay: `${i * 0.5}s` }}>
                    <Icon style={{ width: 22, height: 22, color: 'rgba(10,10,10,.5)', strokeWidth: 1.5 }} />
                  </motion.div>
                  <div style={{ fontFamily: "'Plus Jakarta Sans',sans-serif", fontSize: 'clamp(40px,5vw,56px)', fontWeight: 700, color: '#0A0A0A', letterSpacing: '-.03em', lineHeight: 1.1, marginBottom: 12 }}>
                    <Counter value={s.value} suffix={s.suffix} />
                  </div>
                  <div style={{ fontSize: 14, color: 'rgba(10,10,10,.35)' }}>{s.label}</div>
                </motion.div>
                </TiltCard>
              );
            })}
          </motion.div>
        </div>
      </section>

      <Divider />

      {/* ═══ CAPABILITIES OVERVIEW ═══ */}
      <section style={{ background: '#fff', padding: '140px 40px', position: 'relative', overflow: 'hidden' }} className="sp">
        <div className="grid-bg" style={{ position: 'absolute', inset: 0, zIndex: 0 }} />
        <div className="noise" />
        <FloatingParticles count={15} color="rgba(10,10,10,0.02)" />
        <div style={{ maxWidth: 1400, margin: '0 auto', position: 'relative', zIndex: 1 }}>
          <motion.div variants={stagger} initial="hidden" whileInView="visible" viewport={{ once: false, margin: '-100px' }} style={{ maxWidth: 680, marginBottom: 80 }}>
            <motion.p variants={fadeUp} style={{ fontSize: 13, fontWeight: 600, letterSpacing: '.1em', color: 'rgba(10,10,10,.3)', textTransform: 'uppercase', marginBottom: 20 }}>Capabilities</motion.p>
            <motion.h2 variants={clipReveal} style={{ fontFamily: "'Plus Jakarta Sans',sans-serif", fontSize: 'clamp(36px,5vw,56px)', fontWeight: 700, color: '#0A0A0A', letterSpacing: '-.03em', lineHeight: 1.15, marginBottom: 24 }}>
              Six modules. One platform. <em style={{ fontStyle: 'italic', color: 'rgba(10,10,10,.4)' }}>Zero compromise.</em>
            </motion.h2>
            <motion.p variants={fadeUp} style={{ fontSize: 'clamp(16px,1.8vw,19px)', color: 'rgba(10,10,10,.35)', lineHeight: 1.7 }}>
              Every tool a modern Indian legal practice needs — research, documents, compliance, reasoning, storage, and monitoring — integrated into one intelligent platform.
            </motion.p>
          </motion.div>

          <motion.div className="feat-grid" variants={stagger} initial="hidden" whileInView="visible" viewport={{ once: false, margin: '-60px' }}
            style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 20 }}>
            {CAPABILITIES.map((f) => {
              const Icon = f.icon;
              return (
                <TiltCard key={f.label} strength={8}>
                <motion.div variants={cardUp}
                  whileHover={{ y: -10, borderColor: 'rgba(10,10,10,.14)', backgroundColor: 'rgba(10,10,10,.04)', boxShadow: '0 32px 80px rgba(0,0,0,0.08), 0 0 40px rgba(10,10,10,0.02)' }}
                  className="border-breathe glow-breathe"
                  style={{ position: 'relative', overflow: 'hidden', background: '#fff', border: '1px solid rgba(10,10,10,.06)', borderRadius: 24, padding: '48px 36px', transition: 'all .5s cubic-bezier(.16,1,.3,1)', cursor: 'default', transformStyle: 'preserve-3d' }}>
                  <SpotlightFollow size={300} />
                  {/* Subtle top gradient line on hover */}
                  <motion.div
                    initial={{ scaleX: 0, opacity: 0 }}
                    whileInView={{ scaleX: 1, opacity: 1 }}
                    viewport={{ once: false }}
                    transition={{ delay: 0.3, duration: 1, ease: [0.22, 1, 0.36, 1] }}
                    style={{ position: 'absolute', top: 0, left: '10%', right: '10%', height: 1, background: 'linear-gradient(90deg, transparent, rgba(10,10,10,0.1), transparent)', transformOrigin: 'center' }}
                  />
                  <div style={{ position: 'relative', zIndex: 1 }}>
                    <motion.div
                      whileHover={{ scale: 1.1, borderColor: 'rgba(10,10,10,0.15)' }}
                      className="icon-float"
                      style={{ width: 56, height: 56, borderRadius: 16, background: 'rgba(10,10,10,.04)', border: '1px solid rgba(10,10,10,.08)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 28, transition: 'all .4s cubic-bezier(.16,1,.3,1)' }}>
                      <Icon style={{ width: 24, height: 24, color: '#0A0A0A', strokeWidth: 1.6 }} />
                    </motion.div>
                    <h3 style={{ fontSize: 19, fontWeight: 700, color: '#0A0A0A', marginBottom: 12, letterSpacing: '-.01em' }}>{f.label}</h3>
                    <p style={{ fontSize: 15, color: 'rgba(10,10,10,.4)', lineHeight: 1.75 }}>{f.desc}</p>
                    <motion.div
                      initial={{ width: 0 }}
                      whileInView={{ width: 40 }}
                      viewport={{ once: false }}
                      transition={{ delay: 0.5, duration: 0.8, ease: EASE }}
                      style={{ height: 2, background: 'rgba(10,10,10,0.1)', borderRadius: 1, marginTop: 20 }}
                    />
                  </div>
                </motion.div>
                </TiltCard>
              );
            })}
          </motion.div>
        </div>
      </section>

      <Divider />

      {/* ═══ HOW IT WORKS ═══ */}
      <section style={{ background: '#fff', padding: '140px 40px', position: 'relative', overflow: 'hidden' }} className="sp">
        <div className="noise" />
        <FloatingParticles count={10} color="rgba(10,10,10,0.02)" />
        <div style={{ maxWidth: 1100, margin: '0 auto', position: 'relative', zIndex: 1 }}>
          <motion.div variants={stagger} initial="hidden" whileInView="visible" viewport={{ once: false, margin: '-100px' }} style={{ textAlign: 'center', marginBottom: 80 }}>
            <motion.p variants={fadeUp} style={{ fontSize: 13, fontWeight: 600, letterSpacing: '.1em', color: 'rgba(10,10,10,.3)', textTransform: 'uppercase', marginBottom: 20 }}>How it works</motion.p>
            <motion.h2 variants={clipReveal} style={{ fontFamily: "'Plus Jakarta Sans',sans-serif", fontSize: 'clamp(36px,5vw,56px)', fontWeight: 700, color: '#0A0A0A', letterSpacing: '-.03em', lineHeight: 1.15, maxWidth: 600, margin: '0 auto' }}>
              Three steps to <em style={{ fontStyle: 'italic', color: 'rgba(10,10,10,.4)' }}>clarity.</em>
            </motion.h2>
          </motion.div>

          <motion.div className="work-grid" variants={stagger} initial="hidden" whileInView="visible" viewport={{ once: false, margin: '-60px' }}
            style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 32, position: 'relative' }}>
            {/* Connecting line */}
            <motion.div variants={lineReveal} className="breathe" style={{ position: 'absolute', top: 56, left: '20%', right: '20%', height: 1, background: 'linear-gradient(90deg, transparent, rgba(10,10,10,0.08), rgba(10,10,10,0.08), transparent)', transformOrigin: 'left', zIndex: 0 }} />
            {[
              { num: '01', title: 'Upload or Ask', desc: 'Drop a contract, paste a query, or type a legal question. Spectr understands context instantly.', icon: ArrowUpRight },
              { num: '02', title: 'AI Analyzes', desc: 'Our reasoning engine searches 50M+ judgments, cross-references statutes, and constructs cited arguments.', icon: BrainCircuit },
              { num: '03', title: 'Review & Act', desc: 'Get structured memos, risk flags, reconciliation reports — verified and ready to use in minutes.', icon: CheckCircle2 },
            ].map((step, i) => {
              const StepIcon = step.icon;
              return (
                <motion.div key={step.num} variants={cardUp}
                  style={{ textAlign: 'center', padding: '48px 32px', position: 'relative', zIndex: 1 }}>
                  <motion.div
                    initial={{ scale: 0, opacity: 0 }}
                    whileInView={{ scale: 1, opacity: 1 }}
                    viewport={{ once: false }}
                    transition={{ delay: 0.2 + i * 0.15, duration: 0.6, ease: EASE }}
                    className="icon-float border-breathe"
                    style={{
                      width: 72, height: 72, borderRadius: 22,
                      background: 'rgba(10,10,10,.03)', border: '1px solid rgba(10,10,10,.08)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      margin: '0 auto 28px', position: 'relative',
                      animationDelay: `${i * 0.8}s`,
                    }}>
                    <StepIcon style={{ width: 28, height: 28, color: '#0A0A0A', strokeWidth: 1.4 }} />
                    <OrbitDot size={3} radius={44} duration={6 + i * 2} color="rgba(10,10,10,0.15)" delay={i * 0.5} />
                    <span style={{
                      position: 'absolute', top: -8, right: -8,
                      width: 28, height: 28, borderRadius: 10,
                      background: '#0A0A0A', color: '#fff',
                      fontSize: 11, fontWeight: 800,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontFamily: "'JetBrains Mono', monospace",
                    }}>{step.num}</span>
                  </motion.div>
                  <h3 style={{ fontSize: 20, fontWeight: 700, color: '#0A0A0A', marginBottom: 14, letterSpacing: '-.01em' }}>{step.title}</h3>
                  <p style={{ fontSize: 15, color: 'rgba(10,10,10,.4)', lineHeight: 1.75, maxWidth: 280, margin: '0 auto' }}>{step.desc}</p>
                </motion.div>
              );
            })}
          </motion.div>
        </div>
      </section>

      <Divider />

      {/* ═══ DEEP RESEARCH ENGINE ═══ */}
      <section style={{ background: '#fff', padding: '160px 40px', position: 'relative', overflow: 'hidden' }} className="sp">
        <div className="noise" />
        <FloatingParticles count={18} color="rgba(100,68,245,0.06)" />
        {/* Animated accent lines */}
        <motion.div animate={{ opacity: [0.02, 0.08, 0.02], scaleX: [0.7, 1, 0.7] }} transition={{ duration: 7, repeat: Infinity, ease: 'easeInOut' }}
          style={{ position: 'absolute', top: '25%', left: '5%', width: '90%', height: 1, background: 'linear-gradient(90deg, transparent, rgba(100,68,245,0.12), transparent)', transformOrigin: 'center', pointerEvents: 'none', zIndex: 0 }} />
        <motion.div animate={{ opacity: [0.02, 0.06, 0.02], scaleX: [1, 0.7, 1] }} transition={{ duration: 9, repeat: Infinity, ease: 'easeInOut', delay: 3 }}
          style={{ position: 'absolute', top: '75%', left: '10%', width: '80%', height: 1, background: 'linear-gradient(90deg, transparent, rgba(100,68,245,0.08), transparent)', transformOrigin: 'center', pointerEvents: 'none', zIndex: 0 }} />
        {/* Animated grid background */}
        <div className="grid-bg" style={{ position: 'absolute', inset: 0, zIndex: 0, opacity: 0.5 }} />
        {/* Beam canvas behind */}
        <BeamCanvas style={{ position: 'absolute', inset: 0, zIndex: 0, opacity: 0.12 }} beamCount={16} baseColor="rgba(100,68,245," />

        <div style={{ maxWidth: 1200, margin: '0 auto', position: 'relative', zIndex: 1 }}>
          <motion.div variants={stagger} initial="hidden" whileInView="visible" viewport={{ once: false, margin: '-100px' }} style={{ textAlign: 'center', marginBottom: 80 }}>
            <motion.div variants={blurFadeUp} style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '8px 18px', background: 'rgba(100,68,245,0.08)', border: '1px solid rgba(100,68,245,0.15)', borderRadius: 999, fontSize: 12, fontWeight: 700, color: 'rgba(100,68,245,0.7)', letterSpacing: '.06em', textTransform: 'uppercase', marginBottom: 24 }}>
              <Sparkles style={{ width: 13, height: 13 }} /> New
            </motion.div>
            <motion.h2 variants={clipReveal} style={{ fontFamily: "'Inter',sans-serif", fontSize: 'clamp(36px,5vw,60px)', fontWeight: 500, background: 'linear-gradient(to bottom right, #0A0A0A 40%, rgba(10,10,10,0.45))', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', letterSpacing: '-.05em', lineHeight: 1.1, maxWidth: 800, margin: '0 auto 20px' }}>
              Deep Research that thinks like a senior partner.
            </motion.h2>
            <motion.p variants={fadeUp} style={{ fontSize: 'clamp(16px,1.8vw,19px)', color: 'rgba(10,10,10,.4)', lineHeight: 1.7, maxWidth: 600, margin: '0 auto' }}>
              When a query demands exhaustive analysis, Spectr launches isolated Blaxel sandbox VMs with headless Chromium to investigate across 12+ legal databases — then synthesizes everything with a 6-tier AI cascade.
            </motion.p>
          </motion.div>

          {/* 5-Phase Pipeline Visualization */}
          <motion.div variants={stagger} initial="hidden" whileInView="visible" viewport={{ once: false, margin: '-60px' }}
            style={{ display: 'flex', flexDirection: 'column', gap: 0, maxWidth: 900, margin: '0 auto' }}>
            {[
              { phase: '01', title: 'Broad Intelligence Sweep', desc: '7 targeted queries across IndianKanoon, LiveLaw, SCCOnline, TaxGuru, CBDT, ITAT — 12 pages per search', icon: Globe, color: '#18CCFC', duration: '~15s' },
              { phase: '02', title: 'Entity & Citation Extraction', desc: 'Regex extraction of cases, sections, acts, circulars, and tribunals from Phase 1 results', icon: Search, color: '#6344F5', duration: '~3s' },
              { phase: '03', title: 'Targeted Deep Dive', desc: 'Entity-specific queries — full text of found cases, related judgments, commentary', icon: Target, color: '#AE48FF', duration: '~20s' },
              { phase: '04', title: 'Opposing Counsel Analysis', desc: 'Counter-arguments, conflicting judgments, dissenting opinions, revenue wins', icon: Shield, color: '#FF6B6B', duration: '~15s' },
              { phase: '05', title: 'Timeline & Regulatory History', desc: 'Amendment chronology, circular history, effective date changes for cited sections', icon: Clock, color: '#22C55E', duration: '~10s' },
            ].map((p, i) => (
              <motion.div key={p.phase} variants={cardUp}
                className="border-breathe"
                style={{ display: 'flex', gap: 20, alignItems: 'flex-start', padding: '28px 0', borderBottom: i < 4 ? '1px solid rgba(10,10,10,0.04)' : 'none', position: 'relative' }}>
                {/* Phase number + connecting line */}
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flexShrink: 0, width: 48 }}>
                  <motion.div
                    className="icon-float"
                    initial={{ scale: 0 }}
                    whileInView={{ scale: 1 }}
                    viewport={{ once: false }}
                    transition={{ delay: i * 0.12, duration: 0.5, ease: EASE }}
                    style={{ width: 48, height: 48, borderRadius: 14, background: `${p.color}10`, border: `1px solid ${p.color}25`, display: 'flex', alignItems: 'center', justifyContent: 'center', animationDelay: `${i * 0.6}s` }}>
                    {React.createElement(p.icon, { style: { width: 20, height: 20, color: p.color, strokeWidth: 1.5 } })}
                  </motion.div>
                  {i < 4 && <div style={{ width: 1, height: 28, background: `linear-gradient(to bottom, ${p.color}20, transparent)`, marginTop: 4 }} />}
                </div>
                {/* Content */}
                <div style={{ flex: 1, paddingTop: 4 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                    <span style={{ fontSize: 11, fontWeight: 800, color: p.color, fontFamily: "'JetBrains Mono', monospace" }}>PHASE {p.phase}</span>
                    <span style={{ fontSize: 11, color: 'rgba(10,10,10,0.2)', fontFamily: "'JetBrains Mono', monospace" }}>{p.duration}</span>
                  </div>
                  <h3 style={{ fontSize: 18, fontWeight: 700, color: '#0A0A0A', marginBottom: 6, letterSpacing: '-.01em' }}>{p.title}</h3>
                  <p style={{ fontSize: 14, color: 'rgba(10,10,10,0.4)', lineHeight: 1.6 }}>{p.desc}</p>
                </div>
              </motion.div>
            ))}
          </motion.div>

          {/* Output stats */}
          <motion.div variants={stagger} initial="hidden" whileInView="visible" viewport={{ once: false, margin: '-60px' }}
            style={{ display: 'flex', justifyContent: 'center', gap: 48, marginTop: 64, flexWrap: 'wrap' }}>
            {[
              { value: '60-180s', label: 'Total research time' },
              { value: '50+', label: 'Pages analyzed' },
              { value: '12+', label: 'Legal databases' },
              { value: '4,096MB', label: 'Sandbox RAM' },
            ].map((stat, i) => (
              <motion.div key={stat.label} variants={fadeUp} style={{ textAlign: 'center' }}>
                <div className="icon-float" style={{ fontSize: 28, fontWeight: 800, color: '#0A0A0A', letterSpacing: '-.03em', animationDelay: `${i * 0.4}s` }}>{stat.value}</div>
                <div style={{ fontSize: 12, color: 'rgba(10,10,10,0.25)', marginTop: 4, fontWeight: 500 }}>{stat.label}</div>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      <Divider />

      {/* ═══ BUILT FOR INDIA — hyped replacement ═══ */}
      <section style={{ background: '#fff', padding: '160px 40px', position: 'relative', overflow: 'hidden' }} className="sp">
        <FloatingParticles count={14} color="rgba(10,10,10,0.03)" />
        <CanvasTrails style={{ position: 'absolute', inset: 0, opacity: 0.2, zIndex: 0 }} />
        <div className="noise" />
        <div style={{ maxWidth: 1200, margin: '0 auto', position: 'relative', zIndex: 1 }}>
          <motion.div variants={stagger} initial="hidden" whileInView="visible" viewport={{ once: false, margin: '-100px' }} style={{ textAlign: 'center', marginBottom: 96 }}>
            <motion.p variants={fadeUp} style={{ fontSize: 13, fontWeight: 700, letterSpacing: '.1em', color: 'rgba(10,10,10,.3)', textTransform: 'uppercase', marginBottom: 20 }}>Built for India</motion.p>
            <motion.h2
              initial={{ opacity: 0, scale: 0.92, y: 40 }}
              whileInView={{ opacity: 1, scale: 1, y: 0 }}
              viewport={{ once: false, margin: '-100px' }}
              transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1] }}
              style={{ fontFamily: "'Inter',sans-serif", fontSize: 'clamp(40px,6vw,72px)', fontWeight: 500, background: 'linear-gradient(to bottom right, #0A0A0A 40%, rgba(10,10,10,0.4))', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', letterSpacing: '-.05em', lineHeight: 1.05, maxWidth: 900, margin: '0 auto 20px' }}>
              Verified citations only. Every claim sourced. Zero hallucinations.
            </motion.h2>
            <motion.p variants={fadeUp} style={{ fontSize: 'clamp(16px,1.8vw,19px)', color: 'rgba(10,10,10,.45)', maxWidth: 680, margin: '0 auto', lineHeight: 1.7 }}>
              Every case law, statute, and circular referenced by Spectr is verified against official sources — IndianKanoon, MongoDB Statute DB, CBDT, CBIC, and SEBI. When we cite Smifs Securities, we also tell you it was overruled. When we quote Section 194T, you get the exact effective date.
            </motion.p>
          </motion.div>

          {/* Big numbers that matter */}
          <motion.div variants={stagger} initial="hidden" whileInView="visible" viewport={{ once: false, margin: '-60px' }}
            style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 1, background: 'rgba(10,10,10,0.08)', border: '1px solid rgba(10,10,10,0.08)', borderRadius: 24, overflow: 'hidden', marginBottom: 80 }} className="feat-grid">
            {[
              { big: '<2s', label: 'First answer', sub: 'Groq baseline while deep model thinks' },
              { big: '94%', label: 'Time saved', sub: '3 days of research → 3 minutes' },
              { big: '99.2%', label: 'Citation accuracy', sub: 'Every citation verified against source' },
              { big: '0', label: 'Missed deadlines', sub: 'Proactive regulatory monitoring' },
            ].map((s, i) => (
              <motion.div key={i} variants={cardUp}
                whileHover={{ backgroundColor: 'rgba(10,10,10,0.02)' }}
                style={{ background: '#fff', padding: '48px 32px', textAlign: 'center', transition: 'all 0.4s cubic-bezier(0.16,1,0.3,1)' }}>
                <div className="icon-float" style={{ fontFamily: "'Inter',sans-serif", fontSize: 'clamp(40px,5vw,64px)', fontWeight: 500, background: 'linear-gradient(to bottom right, #0A0A0A 40%, rgba(10,10,10,0.4))', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', letterSpacing: '-.04em', lineHeight: 1, marginBottom: 12, animationDelay: `${i * 0.5}s` }}>
                  {s.big}
                </div>
                <div style={{ fontSize: 14, fontWeight: 700, color: '#0A0A0A', marginBottom: 6, letterSpacing: '-.01em' }}>{s.label}</div>
                <div style={{ fontSize: 12, color: 'rgba(10,10,10,0.35)', lineHeight: 1.5 }}>{s.sub}</div>
              </motion.div>
            ))}
          </motion.div>

          {/* Why different — 3 pillars */}
          <motion.div variants={stagger} initial="hidden" whileInView="visible" viewport={{ once: false, margin: '-60px' }}
            style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 20 }} className="feat-grid">
            {[
              {
                tag: '01',
                title: 'Trained on Indian statutes',
                desc: 'IPC, CPC, CrPC, CGST Act, Companies Act, SEBI, RBI circulars, FEMA — indexed and cross-referenced. Not scraped. Actually understood.',
                icon: BookOpen,
              },
              {
                tag: '02',
                title: 'Zero hallucinations',
                desc: 'Every citation is verified against MongoDB statute DB or IndianKanoon. Known overruled judgments (Smifs, L&T, Vodafone) are explicitly flagged.',
                icon: CheckCircle2,
              },
              {
                tag: '03',
                title: 'Adversarial war-gaming',
                desc: 'Our AI doesn\'t just argue your position. It pre-empts opposing counsel by searching conflicting judgments and revenue wins on the same point.',
                icon: Shield,
              },
            ].map((p, i) => {
              const PIcon = p.icon;
              return (
                <motion.div key={p.tag} variants={cardUp}
                  className="border-breathe"
                  whileHover={{ y: -8, borderColor: 'rgba(10,10,10,0.2)', boxShadow: '0 24px 60px rgba(0,0,0,0.08)' }}
                  style={{ padding: '36px 32px', borderRadius: 20, background: '#fff', border: '1px solid rgba(10,10,10,0.08)', transition: 'all 0.5s cubic-bezier(0.16,1,0.3,1)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
                    <span style={{ fontSize: 11, fontWeight: 800, color: 'rgba(10,10,10,0.25)', fontFamily: "'JetBrains Mono', monospace", letterSpacing: '.1em' }}>{p.tag}</span>
                    <div className="icon-float" style={{ width: 40, height: 40, borderRadius: 12, background: '#0A0A0A', display: 'flex', alignItems: 'center', justifyContent: 'center', animationDelay: `${i * 0.4}s` }}>
                      <PIcon style={{ width: 18, height: 18, color: '#fff', strokeWidth: 1.8 }} />
                    </div>
                  </div>
                  <h3 style={{ fontSize: 20, fontWeight: 700, color: '#0A0A0A', marginBottom: 12, letterSpacing: '-.02em', lineHeight: 1.2 }}>{p.title}</h3>
                  <p style={{ fontSize: 14, color: 'rgba(10,10,10,0.5)', lineHeight: 1.7 }}>{p.desc}</p>
                </motion.div>
              );
            })}
          </motion.div>

          {/* AI engine badge — condensed cascade info */}
          <motion.div variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: false, margin: '-40px' }}
            style={{ marginTop: 64, textAlign: 'center' }}>
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: 14, padding: '12px 24px', background: '#0A0A0A', borderRadius: 999, fontSize: 13, color: '#fff', boxShadow: '0 8px 32px rgba(0,0,0,0.12)' }}>
              <span className="dot-pulse" style={{ width: 6, height: 6, borderRadius: '50%', background: '#22c55e' }} />
              <span style={{ fontWeight: 600 }}>Powered by</span>
              <span style={{ opacity: 0.6, fontFamily: "'JetBrains Mono', monospace", fontSize: 11 }}>
                Gemini 2.5 Pro · Claude 4 · GPT-4o · Groq · +2 more
              </span>
              <span style={{ padding: '3px 8px', background: 'rgba(255,255,255,0.15)', borderRadius: 6, fontSize: 10, fontWeight: 700, letterSpacing: '.04em' }}>6-TIER FAILOVER</span>
            </div>
          </motion.div>
        </div>
      </section>

      <Divider />

      {/* ═══ SPLINE 3D INTERACTIVE ═══ */}
      <section style={{ background: '#fff', padding: '100px 40px', position: 'relative', overflow: 'hidden' }} className="sp">
        <div className="noise" />
        <div style={{ maxWidth: 1100, margin: '0 auto', position: 'relative', zIndex: 1 }}>
          <motion.div variants={stagger} initial="hidden" whileInView="visible" viewport={{ once: false, margin: '-100px' }} style={{ textAlign: 'center', marginBottom: 48 }}>
            <motion.p variants={fadeUp} style={{ fontSize: 13, fontWeight: 600, letterSpacing: '.1em', color: 'rgba(10,10,10,.3)', textTransform: 'uppercase', marginBottom: 20 }}>Experience</motion.p>
            <motion.h2 variants={clipReveal} style={{ fontFamily: "'Plus Jakarta Sans',sans-serif", fontSize: 'clamp(32px,4vw,48px)', fontWeight: 700, color: '#0A0A0A', letterSpacing: '-.03em', lineHeight: 1.15, maxWidth: 600, margin: '0 auto' }}>
              Technology that feels like <em style={{ fontStyle: 'italic', color: 'rgba(10,10,10,.4)' }}>magic.</em>
            </motion.h2>
          </motion.div>
          <motion.div variants={scaleIn} initial="hidden" whileInView="visible" viewport={{ once: false, margin: '-60px' }}>
            <SplineFrame />
          </motion.div>
        </div>
      </section>

      <Divider />

      {/* ═══ CANVAS TRAILS INTERACTIVE ═══ */}
      <section style={{ background: '#fff', padding: '140px 40px', position: 'relative', overflow: 'hidden', minHeight: 500 }} className="sp">
        <div style={{ position: 'absolute', inset: 0, zIndex: 0 }}>
          <CanvasTrails style={{ position: 'absolute', inset: 0, opacity: 0.6 }} />
        </div>
        <div className="noise" />
        <motion.div variants={stagger} initial="hidden" whileInView="visible" viewport={{ once: false, margin: '-100px' }}
          style={{ maxWidth: 700, margin: '0 auto', textAlign: 'center', position: 'relative', zIndex: 2 }}>
          <motion.p variants={fadeUp} style={{ fontSize: 13, fontWeight: 600, letterSpacing: '.1em', color: 'rgba(10,10,10,.3)', textTransform: 'uppercase', marginBottom: 20 }}>Interactive</motion.p>
          <motion.h2 variants={clipReveal} style={{ fontFamily: "'Plus Jakarta Sans',sans-serif", fontSize: 'clamp(32px,4vw,48px)', fontWeight: 700, color: '#0A0A0A', letterSpacing: '-.03em', lineHeight: 1.2, marginBottom: 20, maxWidth: 600, margin: '0 auto 20px' }}>
            Move your cursor. <em style={{ fontStyle: 'italic', color: 'rgba(10,10,10,.4)' }}>Feel the intelligence.</em>
          </motion.h2>
          <motion.p variants={fadeUp} style={{ fontSize: 16, color: 'rgba(10,10,10,.3)', lineHeight: 1.7, maxWidth: 480, margin: '0 auto' }}>
            Every interaction with Spectr is designed to feel responsive, alive, and intentional — because your tools should inspire confidence, not friction.
          </motion.p>
        </motion.div>
      </section>

      <Divider />

      {/* ═══ SECURITY ═══ */}
      <section style={{ background: '#fff', position: 'relative', overflow: 'hidden', padding: '140px 40px' }} className="sp">
        <div style={{ position: 'absolute', inset: 0, zIndex: 0, opacity: 0.4 }}><SmokeBackground smokeColor="#1a1a2e" /></div>
        <div style={{ position: 'absolute', inset: 0, zIndex: 1, background: 'rgba(255,255,255,.6)', pointerEvents: 'none' }} />
        <div className="noise" style={{ zIndex: 1 }} />

        <div style={{ maxWidth: 1100, margin: '0 auto', position: 'relative', zIndex: 2 }}>
          <motion.div variants={stagger} initial="hidden" whileInView="visible" viewport={{ once: false, margin: '-100px' }} style={{ textAlign: 'center', marginBottom: 72 }}>
            <motion.p variants={fadeUp} style={{ fontSize: 13, fontWeight: 600, letterSpacing: '.1em', color: 'rgba(10,10,10,.3)', textTransform: 'uppercase', marginBottom: 20 }}>Security & Privacy</motion.p>
            <motion.h2 variants={clipReveal} style={{ fontFamily: "'Plus Jakarta Sans',sans-serif", fontSize: 'clamp(36px,5vw,56px)', fontWeight: 700, color: '#0A0A0A', letterSpacing: '-.03em', lineHeight: 1.15, maxWidth: 700, margin: '0 auto' }}>
              Your data never trains anyone else's <em style={{ fontStyle: 'italic', color: 'rgba(10,10,10,.4)' }}>model.</em>
            </motion.h2>
          </motion.div>

          <motion.div className="sec-grid" variants={stagger} initial="hidden" whileInView="visible" viewport={{ once: false, margin: '-60px' }}
            style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 20 }}>
            {SECURITY_CARDS.map(card => {
              const SIcon = card.icon;
              return (
                <motion.div key={card.label} variants={cardUp} whileHover={{ borderColor: 'rgba(10,10,10,.14)', backgroundColor: 'rgba(10,10,10,.05)', y: -6 }}
                  className="border-breathe glow-breathe"
                  style={{ background: 'rgba(10,10,10,.03)', border: '1px solid rgba(10,10,10,.06)', borderRadius: 24, padding: '44px 36px', transition: 'all .5s cubic-bezier(.16,1,.3,1)', position: 'relative', overflow: 'hidden' }}>
                  <SpotlightFollow size={250} />
                  <div style={{ position: 'relative', zIndex: 1 }}>
                    <div style={{ width: 52, height: 52, borderRadius: 14, background: 'rgba(10,10,10,.05)', border: '1px solid rgba(10,10,10,.08)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 28 }}>
                      <SIcon style={{ width: 22, height: 22, color: 'rgba(10,10,10,.6)', strokeWidth: 1.6 }} />
                    </div>
                    <h3 style={{ fontSize: 19, fontWeight: 700, color: '#0A0A0A', marginBottom: 12, letterSpacing: '-.01em' }}>{card.label}</h3>
                    <p style={{ fontSize: 15, color: 'rgba(10,10,10,.4)', lineHeight: 1.7 }}>{card.desc}</p>
                  </div>
                </motion.div>
              );
            })}
          </motion.div>
        </div>
      </section>

      <Divider />

      {/* ═══ INTERACTIVE AI DEMO ═══ */}
      <section style={{ background: '#fff', padding: '140px 40px 80px', position: 'relative', overflow: 'hidden' }} className="sp">
        <div className="noise" />
        <div style={{ position: 'absolute', inset: 0, zIndex: 0 }}>
          <BeamCanvas style={{ position: 'absolute', inset: 0, opacity: 0.15 }} beamCount={12} baseColor="rgba(100,68,245," />
        </div>
        <div style={{ maxWidth: 1100, margin: '0 auto', position: 'relative', zIndex: 1 }}>
          <motion.div variants={stagger} initial="hidden" whileInView="visible" viewport={{ once: false, margin: '-100px' }} style={{ textAlign: 'center', marginBottom: 60 }}>
            <motion.div variants={blurFadeUp} style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '8px 18px', background: 'rgba(10,10,10,.03)', border: '1px solid rgba(10,10,10,.06)', borderRadius: 999, fontSize: 12, fontWeight: 600, color: 'rgba(10,10,10,.4)', letterSpacing: '.06em', textTransform: 'uppercase', marginBottom: 24 }}>
              <Bot style={{ width: 14, height: 14, strokeWidth: 1.5 }} /> Live AI Demo
            </motion.div>
            <motion.h2 variants={clipReveal} style={{ fontFamily: "'Plus Jakarta Sans',sans-serif", fontSize: 'clamp(32px,4.5vw,52px)', fontWeight: 700, color: '#0A0A0A', letterSpacing: '-.03em', lineHeight: 1.15, maxWidth: 700, margin: '0 auto 20px' }}>
              Meet Spectr <em style={{ fontStyle: 'italic', color: 'rgba(10,10,10,.4)' }}>Your AI legal partner.</em>
            </motion.h2>
            <motion.p variants={fadeUp} style={{ fontSize: 16, color: 'rgba(10,10,10,.3)', maxWidth: 520, margin: '0 auto', lineHeight: 1.7 }}>
              Watch Spectr research, reason, and respond — in real time. This is what AI-native legal intelligence looks like.
            </motion.p>
          </motion.div>
          <SpectrAIDemo />
        </div>
      </section>

      {/* ═══ CINEMATIC FOOTER ═══ */}
      <CinematicFooter onGetStarted={go} />
    </div>
    </>
  );
}
