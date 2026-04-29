import React, { useState, useRef, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '../context/AuthContext';
import ResponseCard from '../components/ResponseCard';
import api from '../services/api';
import { CubeLoader } from '../components/ui/cube-loader';
import { TrustScoreBadge } from '../components/TrustScoreBadge';
import { DriveUploadButton } from '../components/DriveUploadButton';
import { PlaybookPicker } from '../components/PlaybookPicker';
import { AgentProgressPanel, useAgentStream } from '../components/AgentProgressPanel';
import { DeepResearchViz } from '../components/DeepResearchViz';
import {
  Plus, FileText, Loader2,
  Paperclip, ArrowUp, X, ChevronDown, Scale, ArrowRight,
  MessageSquare, Receipt, Calculator, ArrowLeftRight, FileWarning, Shield,
  Zap, Sparkles, FolderOpen, Gavel, FileCheck, Building2, Stamp,
  Timer, Search, BarChart3, Globe, BrainCircuit, Clock, Bookmark,
  ChevronRight,
} from 'lucide-react';

// NOTE: Use 127.0.0.1 (not localhost) in dev — on Windows, Chrome's Happy Eyeballs
// resolves `localhost` to IPv6 `[::1]` first. If uvicorn binds only IPv4, Chrome throws
// "Failed to fetch" on the IPv6 refusal without reliably falling back to IPv4.
const API = process.env.NODE_ENV === 'development' ? '/api' : '/api';

const MODE_CATEGORIES = [
  { id: 'research', label: 'Research', icon: Search },
  { id: 'tax', label: 'Tax & GST', icon: Calculator },
  { id: 'legal', label: 'Legal', icon: Gavel },
  { id: 'documents', label: 'Documents', icon: FileCheck },
];

const MODES = [
  { id: 'assistant', label: 'Assistant', description: 'Legal & tax AI — 8-step pipeline', icon: MessageSquare, placeholder: 'Ask anything about Indian law, GST, or case law...', isChat: true, category: 'research' },
  { id: 'caselaw', label: 'Case Law', description: 'IndianKanoon AI-ranked search', icon: Scale, placeholder: 'Describe your legal scenario...', isChat: true, category: 'research' },
  { id: 'tds', label: 'TDS Classifier', icon: Receipt, description: 'Detect section & rate', placeholder: 'Describe the payment...', category: 'tax', endpoint: '/tools/tds-classifier',
    params: [
      { key: 'amount', label: 'Amount (₹)', type: 'number', placeholder: '100000' },
      { key: 'payee_type', label: 'Payee', type: 'select', default: 'individual', options: [{ value: 'individual', label: 'Individual / HUF' }, { value: 'company', label: 'Company' }, { value: 'firm', label: 'Firm' }] },
    ],
    buildRequest: (query, p) => ({ description: query, amount: parseFloat(p.amount) || 0, payee_type: p.payee_type || 'individual', is_non_filer: false }),
    formatResponse: (d) => { if (d.error) return d.error; return `## Section ${d.section}\n**${d.title}**\n\n| Parameter | Value |\n|---|---|\n| Rate | ${d.rate_percent ?? d.rate}% |\n| Threshold | ₹${d.threshold?.toLocaleString('en-IN') || 'N/A'} |\n| TDS Amount | ₹${d.tds_amount?.toLocaleString('en-IN') || 'N/A'} |${d.note ? '\n\n> ' + d.note : ''}`; },
  },
  { id: 'penalty', label: 'Penalty Calc', icon: Calculator, description: 'Late filing penalties', placeholder: 'Notes (optional)...', category: 'tax', endpoint: '/tools/penalty-calculator',
    params: [
      { key: 'deadline_type', label: 'Type', type: 'select', default: 'gstr3b', options: [{ value: 'gstr3b', label: 'GSTR-3B' }, { value: 'gstr1', label: 'GSTR-1' }, { value: 'gstr9', label: 'GSTR-9' }, { value: 'itr', label: 'ITR' }, { value: 'tds_return', label: 'TDS Return' }, { value: 'roc', label: 'ROC' }] },
      { key: 'due_date', label: 'Due date', type: 'date' },
      { key: 'actual_date', label: 'Filing date', type: 'date' },
      { key: 'tax_amount', label: 'Tax (₹)', type: 'number', placeholder: '50000' },
    ],
    buildRequest: (_q, p) => ({ deadline_type: p.deadline_type || 'gstr3b', due_date: p.due_date, actual_date: p.actual_date, tax_amount: parseFloat(p.tax_amount) || 0 }),
    formatResponse: (d) => { if (d.error) return d.error; return `## Penalty Computation\n**Delay: ${d.days_late ?? d.delay_days} days**\n\n| Component | Amount |\n|---|---|\n| Late Fee | ₹${(d.late_fee ?? 0).toLocaleString('en-IN')} |\n| Interest | ₹${(d.interest ?? 0).toLocaleString('en-IN')} |\n| **Total** | **₹${(d.total_exposure ?? d.total_penalty ?? 0).toLocaleString('en-IN')}** |${d.legal_basis || d.penalty_type ? '\n\n**Legal Basis:** ' + (d.penalty_type || d.legal_basis) : ''}${d.tip ? '\n\n> ' + d.tip : ''}`; },
  },
  { id: 'mapper', label: 'Section Map', icon: ArrowLeftRight, description: 'IPC/CrPC ↔ BNS/BNSS', placeholder: 'Enter section number (e.g., 420, 302)...', category: 'legal', endpoint: '/tools/section-mapper',
    params: [{ key: 'direction', label: 'Direction', type: 'select', default: 'old_to_new', options: [{ value: 'old_to_new', label: 'Old → New' }, { value: 'new_to_old', label: 'New → Old' }] }],
    buildRequest: (query, p) => ({ section: query.trim(), direction: p.direction || 'old_to_new' }),
    formatResponse: (d) => { if (!d.found) return d.error || 'Section not found.'; return `## ${d.old_section} → ${d.new_section}\n**${d.title}**\n\n| Old | New |\n|---|---|\n| ${d.old_section} | ${d.new_section} |${d.effective_from ? '\n\nEffective from: ' + d.effective_from : ''}${d.note ? '\n\n> ' + d.note : ''}`; },
  },
  { id: 'notice-reply', label: 'Notice Reply', icon: FileWarning, description: 'Auto-draft legal replies', placeholder: 'Paste the full notice text here...', category: 'legal', endpoint: '/tools/notice-auto-reply',
    params: [{ key: 'client_name', label: 'Client', type: 'text', placeholder: 'M/s Sharma Enterprises' }],
    buildRequest: (query, p) => ({ notice_text: query, client_name: p.client_name || '', additional_context: '' }),
    formatResponse: (d) => { if (d.error) return d.error; let r = ''; if (d.notice_type) r += `**Notice Type:** ${d.notice_type}\n`; if (d.demand_amount) r += `**Demand:** ₹${d.demand_amount?.toLocaleString('en-IN')}\n`; if (d.auto_reply) r += '---\n\n' + d.auto_reply; return r || 'No reply generated.'; },
  },
  { id: 'notice-check', label: 'Notice Check', icon: Shield, description: 'Validity & jurisdiction', placeholder: 'Notes (optional)...', category: 'legal', endpoint: '/tools/notice-checker',
    params: [
      { key: 'notice_type', label: 'Type', type: 'select', default: '73', options: [{ value: '73', label: 'GST S.73' }, { value: '74', label: 'GST S.74' }, { value: '143(2)', label: 'IT S.143(2)' }, { value: '148', label: 'IT S.148/148A' }] },
      { key: 'notice_date', label: 'Notice date', type: 'date' },
      { key: 'financial_year', label: 'FY', type: 'text', placeholder: '2022-23' },
    ],
    buildRequest: (_q, p) => ({ notice_type: p.notice_type || '73', notice_date: p.notice_date, financial_year: p.financial_year || '', assessment_year: '', has_din: true, is_fraud_alleged: false }),
    formatResponse: (d) => { if (d.error) return d.error; let r = `## ${d.overall_validity}\n\n`; if (d.limitation_check) r += `**Limitation:** ${d.limitation_check}\n\n`; if (d.challenge_grounds?.length) { r += '### Challenge Grounds\n'; d.challenge_grounds.forEach(g => { r += `- **${g.ground}** [${g.severity}]: ${g.legal_basis}${g.case_law ? ' — *' + g.case_law + '*' : ''}\n`; }); } else { r += '> No challenge grounds found.'; } return r; },
  },
  /* ── New tools from backend ── */
  { id: 'itr', label: 'ITR Compute', icon: BarChart3, description: 'Full tax computation + regime compare', placeholder: 'Enter income details (CTC, deductions)...', category: 'tax', endpoint: '/tools/income-tax/compare-regimes',
    params: [
      { key: 'gross_income', label: 'Gross Income (₹)', type: 'number', placeholder: '2800000' },
      { key: 'hra', label: 'HRA (₹)', type: 'number', placeholder: '360000' },
      { key: 'deductions_80c', label: '80C (₹)', type: 'number', placeholder: '150000' },
    ],
    buildRequest: (query, p) => ({ gross_income: parseFloat(p.gross_income) || 0, hra: parseFloat(p.hra) || 0, deductions_80c: parseFloat(p.deductions_80c) || 0, notes: query }),
    formatResponse: (d) => { if (d.error) return d.error; return `## Tax Computation\n\n**Old Regime:** ₹${(d.old_regime_tax ?? 0).toLocaleString('en-IN')}\n**New Regime:** ₹${(d.new_regime_tax ?? 0).toLocaleString('en-IN')}\n\n**Recommendation:** ${d.recommendation || 'Compare both regimes'}${d.savings ? '\n\n**Savings:** ₹' + d.savings.toLocaleString('en-IN') : ''}`; },
  },
  { id: 'limitation', label: 'Limitation', icon: Timer, description: 'Limitation period calculator', placeholder: 'Describe the cause of action...', category: 'legal', endpoint: '/tools/limitation',
    params: [
      { key: 'cause_type', label: 'Type', type: 'select', default: 'civil_suit', options: [{ value: 'civil_suit', label: 'Civil Suit' }, { value: 'criminal', label: 'Criminal' }, { value: 'appeal', label: 'Appeal' }, { value: 'tax', label: 'Tax Assessment' }] },
      { key: 'accrual_date', label: 'Accrual date', type: 'date' },
    ],
    buildRequest: (query, p) => ({ cause_type: p.cause_type || 'civil_suit', accrual_date: p.accrual_date, description: query }),
    formatResponse: (d) => { if (d.error) return d.error; return `## Limitation Period\n\n**Period:** ${d.limitation_period || d.period}\n**Deadline:** ${d.deadline || d.expiry_date}\n**Status:** ${d.status || (d.is_barred ? '⚠️ Time-barred' : '✅ Within limitation')}${d.legal_basis ? '\n\n**Legal Basis:** ' + d.legal_basis : ''}${d.exceptions?.length ? '\n\n### Exceptions\n' + d.exceptions.map(e => '- ' + e).join('\n') : ''}`; },
  },
  { id: 'stamp-duty', label: 'Stamp Duty', icon: Stamp, description: 'Stamp duty + registration fees', placeholder: 'Notes (optional)...', category: 'legal', endpoint: '/tools/stamp-duty',
    params: [
      { key: 'state', label: 'State', type: 'select', default: 'maharashtra', options: [{ value: 'maharashtra', label: 'Maharashtra' }, { value: 'karnataka', label: 'Karnataka' }, { value: 'delhi', label: 'Delhi' }, { value: 'tamil_nadu', label: 'Tamil Nadu' }, { value: 'gujarat', label: 'Gujarat' }] },
      { key: 'instrument', label: 'Instrument', type: 'select', default: 'sale_deed', options: [{ value: 'sale_deed', label: 'Sale Deed' }, { value: 'gift_deed', label: 'Gift Deed' }, { value: 'lease_deed', label: 'Lease Deed' }, { value: 'mortgage', label: 'Mortgage' }, { value: 'power_of_attorney', label: 'Power of Attorney' }] },
      { key: 'value', label: 'Value (₹)', type: 'number', placeholder: '5000000' },
    ],
    buildRequest: (_q, p) => ({ state: p.state || 'maharashtra', instrument_type: p.instrument || 'sale_deed', transaction_value: parseFloat(p.value) || 0 }),
    formatResponse: (d) => { if (d.error) return d.error; return `## Stamp Duty Calculation\n\n| Component | Amount |\n|---|---|\n| Stamp Duty | ₹${(d.stamp_duty ?? 0).toLocaleString('en-IN')} |\n| Registration | ₹${(d.registration_fee ?? 0).toLocaleString('en-IN')} |\n| **Total** | **₹${(d.total ?? 0).toLocaleString('en-IN')}** |${d.notes ? '\n\n> ' + d.notes : ''}`; },
  },
  { id: 'due-diligence', label: 'Due Diligence', icon: Building2, description: 'DD checklist + red flags', placeholder: 'Describe the transaction or entity...', category: 'documents', isChat: true },
  { id: 'contract', label: 'Contract Review', icon: FileCheck, description: 'Redline + risk scoring', placeholder: 'Paste contract text or upload file...', category: 'documents', isChat: true },
];

const SUGGESTED = [
  { label: 'GST Show-Cause Notice', icon: FileWarning, text: 'My client received a S.74 SCN for ITC mismatch of ₹48L. The demand was issued 3 years after the relevant date. What are our options?', preview: 'Validity, limitation & challenge grounds', category: 'legal' },
  { label: 'TDS Classification', icon: Receipt, text: 'Classify TDS for: web developer ₹5L, office rent ₹8L to individual, freight ₹12L, CA retainer ₹3L. Compute amounts.', preview: 'Multi-payment TDS analysis', category: 'tax' },
  { label: 'Tax Regime Compare', icon: Calculator, text: 'CTC ₹28L. HRA ₹3.6L, 80C ₹1.5L, 80D ₹25K, NPS ₹50K, HBA interest ₹2L. Compare for AY 2026-27.', preview: 'Side-by-side with full breakdowns', category: 'tax' },
  { label: 'Bail under BNS', icon: Scale, text: 'Client charged under S.318/316 BNS (old S.420/406 IPC). First-time offender. Compare regular vs anticipatory bail.', preview: 'Defense strategy with section mapping', category: 'legal' },
  { label: 'Deep Research — Due Diligence', icon: Building2, text: 'Conduct due diligence on Reliance Retail acquisition of Metro Cash & Carry. Check regulatory approvals, CCI filings, FEMA compliance, and litigation history.', preview: '5-phase sandbox investigation', category: 'research' },
  { label: 'Contract Redline', icon: FileCheck, text: 'Review this SaaS agreement for liability caps, indemnification, termination clauses, IP assignment, and non-compete. Flag all high-risk clauses.', preview: 'Clause-level risk scoring', category: 'documents' },
  { label: 'GSTR-2B Reconciliation', icon: BarChart3, text: 'Reconcile GSTR-2B for GSTIN 27AAACR5055K1ZK for FY 2024-25. Compare with purchase register and flag ITC mismatches.', preview: 'Vendor-wise reconciliation', category: 'tax' },
  { label: 'Limitation Period', icon: Timer, text: 'Client wants to challenge IT assessment order dated 15-Mar-2022 for AY 2019-20. Is the limitation period still open?', preview: 'Deadline + exception analysis', category: 'legal' },
];

const THINKING_STEPS_QUICK = [
  'Classifying query...', 'Auto-detecting tools...', 'Searching statutes...',
  'Querying IndianKanoon...', 'Google Search + Scholar...', 'Synthesizing fast baseline...',
];

// Client-side mirror of backend triage gate — suppresses the fake research pipeline UI
// for greetings/casual messages so we don't look like a try-hard for a "hi".
const _GREETING_WORDS = new Set([
  'hi', 'hello', 'hey', 'yo', 'hiya', 'howdy', 'sup', 'whatsup', 'whats', 'wassup',
  'greetings', 'namaste', 'namaskar', 'morning', 'afternoon', 'evening', 'gm', 'gn',
  'thanks', 'thank', 'thankyou', 'ty', 'thx', 'cheers', 'welcome',
  'ok', 'okay', 'k', 'kk', 'cool', 'nice', 'great', 'got', 'it', 'awesome',
  'bye', 'goodbye', 'cya', 'later',
  'yes', 'no', 'yeah', 'yep', 'nope', 'sure', 'alright', 'fine',
  'who', 'are', 'you', 'what', 'is', 'this', 'can', 'do', 'how',
  'test', 'testing', 'ping', 'hola', 'ola',
]);
const _LEGAL_KEYWORDS = [
  'gst', 'tax', 'tds', 'itr', 'section', 'notice', 'scn', 'penalty', 'appeal',
  'bail', 'contract', 'agreement', 'clause', 'case', 'court', 'tribunal',
  'assessment', 'limitation', 'fema', 'sebi', 'companies act', 'cgst', 'ipc',
  'bns', 'crpc', 'rti', 'writ', 'petition', 'draft', 'reply', 'compute',
  'compliance', 'audit', 'reconcile', 'demand', 'interest', 'deduction',
  'itc', 'invoice', 'gstr', '194', 'fy ', 'ay ', '₹', 'rs.', 'rs ',
  'crore', 'lakh', 'client', 'advocate', 'lawyer', 'ca ',
];
function isTrivialQuery(q) {
  if (!q) return false;
  const clean = q.trim().toLowerCase();
  if (clean.length === 0) return false;
  const tokens = clean.replace(/[^\w\s]/g, '').split(/\s+/).filter(Boolean);
  if (tokens.length <= 6 && tokens.every(t => _GREETING_WORDS.has(t))) return true;
  if (clean.length < 60) {
    const hasLegal = _LEGAL_KEYWORDS.some(kw => clean.includes(kw));
    if (!hasLegal) return true;
  }
  return false;
}

const THINKING_STEPS_RESEARCH = [
  'Classifying query & detecting tools...', 'Searching statute database...',
  'Querying IndianKanoon (top 5)...', 'Google Web + News + Scholar (parallel)...',
  'Synthesizing with Claude Sonnet 4.5...', 'Adversarial self-review (partner gate)...',
  'Verifying every citation live...',
];

const THINKING_STEPS_DEEP = [
  'Classifying query & detecting tools...', 'Searching statute database...',
  'Querying IndianKanoon (top 5)...', 'Google Web + News + Scholar (parallel)...',
  'Phase 1: Broad intelligence sweep (12 sources)...', 'Phase 2: Extracting entities & citations...',
  'Phase 3: Targeted deep dive on entities...', 'Phase 4: Opposing counsel + stay-order hunt...',
  'Phase 5: Legislative timeline & amendments...', 'Building research dossier...',
  'Synthesizing with Claude Opus 4.1...', 'Verifying all citations...',
];

// TWO-TIER MODES (unified 23 Apr 2026 — "research" and "partner" merged on backend).
//   everyday → Quick: Haiku fast-path only, ~3–8s, for rate/threshold/definition lookups
//   research → Research: full depth stack — sandbox browser + Serper + IndianKanoon live +
//              Claude Sonnet cascade + Opus escalation + 4,000+ word partner memo. ~2–4 min.
const RESEARCH_MODES = [
  { id: 'everyday', label: 'Quick', desc: 'Instant — ~8s', icon: Zap, badge: null, steps: THINKING_STEPS_QUICK },
  { id: 'research', label: 'Research', desc: 'Partner-grade depth — ~2–4 min', icon: Sparkles, badge: null, steps: THINKING_STEPS_DEEP },
];

export default function AssistantPage() {
  const { getToken, user } = useAuth();
  const [searchParams] = useSearchParams();
  const clientName = searchParams.get('clientName');
  const [query, setQuery] = useState('');
  const [analysisMode, setAnalysisMode] = useState('research');
  const [activeMode, setActiveMode] = useState('assistant');
  const [toolParams, setToolParams] = useState({});
  const [loading, setLoading] = useState(false);
  const [thinkingStep, setThinkingStep] = useState(0);
  const [isTriageLoading, setIsTriageLoading] = useState(false);
  const [conversations, setConversations] = useState(() => {
    // Restore on mount so tab-switching back to /app/assistant preserves the
    // in-progress response instead of starting over. Stored in sessionStorage
    // so it lasts the tab session but doesn't pollute across logins.
    try {
      const raw = sessionStorage.getItem('spectr_active_conversations');
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) return parsed;
      }
    } catch { /* ignore */ }
    return [];
  });
  const [matters, setMatters] = useState([]);
  const [selectedMatter, setSelectedMatter] = useState('');
  const [showMatterDropdown, setShowMatterDropdown] = useState(false);
  const [attachedFile, setAttachedFile] = useState(null);
  const [attachedFiles, setAttachedFiles] = useState([]);     // Task 5: multi-file
  const [showModeSelector, setShowModeSelector] = useState(false);
  const [showResearchDropdown, setShowResearchDropdown] = useState(false);
  const [showPlaybooks, setShowPlaybooks] = useState(false);  // Task 9
  const [selectedPlaybook, setSelectedPlaybook] = useState(null); // Task 9
  const [lastGeneratedFile, setLastGeneratedFile] = useState(null); // Task 6: edit tracking
  const modeSelectorRef = useRef(null);
  const researchDropdownRef = useRef(null);
  const responseEndRef = useRef(null);
  const inputRef = useRef(null);
  const stepTimerRef = useRef(null);
  const fileInputRef = useRef(null);
  const textareaRef = useRef(null);
  const matterRef = useRef(null);
  const nav = useNavigate();

  const currentMode = MODES.find(m => m.id === activeMode) || MODES[0];
  const hasConversations = conversations.length > 0;

  const handleNewThread = () => {
    setConversations([]);
    setQuery('');
    setAttachedFile(null);
    setAttachedFiles([]);
    setSelectedMatter('');
    setShowMatterDropdown(false);
    window.__spectr_active_thread_id = '';  // backend will create a fresh thread
    try {
      sessionStorage.removeItem('spectr_active_conversations');
      sessionStorage.removeItem('spectr_active_thread_id');
    } catch { /**/ }
    setTimeout(() => inputRef.current?.focus(), 50);
  };

  useEffect(() => { fetchMatters(); }, []); // eslint-disable-line

  useEffect(() => {
    if (responseEndRef.current) responseEndRef.current.scrollIntoView({ behavior: 'smooth' });
  }, [conversations]);

  // Persist conversations to sessionStorage on every change so switching
  // tabs and coming back doesn't lose the in-flight reply or restart
  // generation. Cap payload at 1MB so very long responses don't bloat
  // sessionStorage beyond the browser's quota.
  useEffect(() => {
    try {
      const payload = JSON.stringify(conversations);
      if (payload.length < 1_000_000) {
        sessionStorage.setItem('spectr_active_conversations', payload);
      }
    } catch { /* quota or serialisation — ignore */ }
  }, [conversations]);

  // Restore the active thread_id on mount so follow-ups keep landing in the
  // same thread after a tab switch.
  useEffect(() => {
    const saved = sessionStorage.getItem('spectr_active_thread_id');
    if (saved) window.__spectr_active_thread_id = saved;
    const onChange = () => {
      sessionStorage.setItem('spectr_active_thread_id', window.__spectr_active_thread_id || '');
    };
    window.addEventListener('spectr:thread-created', onChange);
    return () => window.removeEventListener('spectr:thread-created', onChange);
  }, []);

  // Listen for PreviousChatsSidebar events — it broadcasts these when the
  // user clicks a past thread or the "New chat" button in the left rail.
  useEffect(() => {
    const onLoadHistory = (e) => {
      const item = e.detail;
      if (!item) return;

      // NEW: thread payload with multiple messages — rehydrate the whole
      // conversation so the user sees every back-and-forth, and set
      // activeThreadId so follow-up messages continue this thread.
      const isThread = item._is_thread || (Array.isArray(item.messages) && item.thread);
      if (isThread && Array.isArray(item.messages)) {
        const rebuilt = [];
        for (const m of item.messages) {
          const tid = `m_${m.history_id || Math.random().toString(36).slice(2, 10)}`;
          rebuilt.push({ id: tid, type: 'query', text: m.query || '' });
          rebuilt.push({
            id: `r_${tid}`,
            type: 'response',
            isStreaming: false,
            data: {
              response_text: m.response_text || m.response || '',
              sections: m.sections || [],
              sources: m.sources || [],
              model_used: m.model_used,
              citations_count: m.citations_count,
              trust_score: m.trust_score,
              verification: m.verification,
              download_urls: m.download_urls || [],
            },
          });
        }
        setConversations(rebuilt);
        if (item.thread?.thread_id || item.thread_id) {
          // Expose on window so handleChatSubmit can pick it up as thread_id
          // on the next /assistant/query POST (no prop drilling needed).
          window.__spectr_active_thread_id = item.thread?.thread_id || item.thread_id;
        }
        const lastMode = item.messages[item.messages.length - 1]?.mode;
        if (lastMode) setAnalysisMode(lastMode);
        return;
      }

      // Legacy: single query_history row (pre-threading)
      const tempId = `h_${item.history_id || Date.now()}`;
      setConversations([
        { id: tempId, type: 'query', text: item.query },
        {
          id: `r_${tempId}`,
          type: 'response',
          isStreaming: false,
          data: {
            response_text: item.response_text || item.response || '',
            sections: item.sections || [],
            sources: item.sources || [],
            model_used: item.model_used,
            citations_count: item.citations_count,
            trust_score: item.trust_score,
            verification: item.verification,
            download_urls: item.download_urls || [],
          },
        },
      ]);
      if (item.mode) setAnalysisMode(item.mode);
      window.__spectr_active_thread_id = '';  // clear; legacy rows aren't threads
    };
    const onNewThread = () => { handleNewThread(); };
    window.addEventListener('spectr:load-history', onLoadHistory);
    window.addEventListener('spectr:new-thread', onNewThread);
    return () => {
      window.removeEventListener('spectr:load-history', onLoadHistory);
      window.removeEventListener('spectr:new-thread', onNewThread);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const currentResearchMode = RESEARCH_MODES.find(m => m.id === analysisMode) || RESEARCH_MODES[0];
  const THINKING_STEPS = currentResearchMode.steps;

  useEffect(() => {
    if (loading && currentMode.isChat && !isTriageLoading) {
      let i = 0;
      const interval = analysisMode === 'partner' ? 3500 : 1800;
      stepTimerRef.current = setInterval(() => { i = (i + 1) % THINKING_STEPS.length; setThinkingStep(i); }, interval);
    } else { clearInterval(stepTimerRef.current); setThinkingStep(0); }
    return () => clearInterval(stepTimerRef.current);
  }, [loading, currentMode.isChat, analysisMode, THINKING_STEPS.length, isTriageLoading]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + 'px';
    }
  }, [query]);

  useEffect(() => {
    const h = (e) => {
      if (matterRef.current && !matterRef.current.contains(e.target)) setShowMatterDropdown(false);
      if (modeSelectorRef.current && !modeSelectorRef.current.contains(e.target)) setShowModeSelector(false);
      if (researchDropdownRef.current && !researchDropdownRef.current.contains(e.target)) setShowResearchDropdown(false);
    };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, []);

  const fetchMatters = async () => {
    try {
      let token = '';

      try { token = await getToken() || token; } catch { /**/ }
      const res = await fetch(`${API}/matters`, { headers: { 'Authorization': `Bearer ${token}` }, credentials: 'include' });
      if (res.ok) setMatters(await res.json());
    } catch { /**/ }
  };

  const updateParam = (key, value) => setToolParams(prev => ({ ...prev, [key]: value }));

  const handleSubmit = async (e, forcedQuery = null) => {
    e?.preventDefault();
    const queryText = (forcedQuery || query).trim();
    if (!queryText && currentMode.isChat) return;
    if (loading) return;
    setQuery(''); setAttachedFile(null); setLoading(true);
    setIsTriageLoading(currentMode.isChat && isTrivialQuery(queryText));
    const tempId = Date.now().toString();
    const displayQuery = currentMode.isChat ? queryText : `[${currentMode.label}] ${queryText || '(structured input)'}`;
    setConversations(prev => [...prev,
      { id: `q_${tempId}`, type: 'query', text: displayQuery, timestamp: new Date() },
      { id: `r_${tempId}`, type: 'response', data: { response_text: '' }, isStreaming: true, timestamp: new Date() },
    ]);
    if (currentMode.isChat) await handleChatSubmit(queryText, tempId);
    else await handleToolSubmit(queryText, tempId);
    setLoading(false);
  };

  const updateResponse = (tempId, patch) => {
    setConversations(prev => prev.map(msg =>
      msg.id === `r_${tempId}` ? { ...msg, ...patch, data: { ...(msg.data || {}), ...(patch.data || {}) } } : msg
    ));
  };

  // Puter.js + Opus 4.7 flow for partner (Deep Research) mode — browser-side reasoning
  const handleOpusAdvisory = async (queryText, tempId) => {
    let token = '';

    try { token = await getToken() || token; } catch { /**/ }
    try { token = await getToken() || token; } catch { /**/ }

    // Check Puter.js loaded
    if (typeof window.puter === 'undefined') {
      console.warn('Puter.js not loaded, falling back to backend');
      return false;
    }

    try {
      updateResponse(tempId, { data: { response_text: '', internal_strategy: 'Gathering statute DB + IndianKanoon + pre-flight context...' } });

      // 1. Get full context from backend — omit matter_id when null (backend expects str, not Optional[str])
      const ctxBody = { query: queryText, conversation_history: [] };
      if (selectedMatter) ctxBody.matter_id = selectedMatter;
      const ctxResp = await fetch(`${API}/assistant/prepare-context`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        credentials: 'include',
        body: JSON.stringify(ctxBody),
      });
      if (!ctxResp.ok) throw new Error(`prepare-context failed: ${ctxResp.status}`);
      const { system_prompt, user_content, sources_used, context_sizes } = await ctxResp.json();

      updateResponse(tempId, { data: { response_text: '', internal_strategy: `Running Claude Opus 4.7 (context: ${context_sizes?.total_user || 0} chars, ${sources_used?.length || 0} IK cases)...` } });

      // 2. Stream Claude Opus 4.7 via Puter.js (FREE, browser-side)
      let fullResponse = '';
      try {
        const stream = await window.puter.ai.chat(
          `${system_prompt}\n\n===\n\n${user_content}`,
          { model: 'claude-opus-4-7', stream: true }
        );
        for await (const part of stream) {
          const chunk = part?.text || '';
          if (chunk) {
            fullResponse += chunk;
            updateResponse(tempId, { data: { response_text: fullResponse, models_used: ['claude-opus-4-7'], sections: (sources_used || []).map(s => s.title) } });
          }
        }
      } catch (streamErr) {
        console.warn('Puter streaming failed, trying non-stream:', streamErr);
        try {
          const response = await window.puter.ai.chat(
            `${system_prompt}\n\n===\n\n${user_content}`,
            { model: 'claude-opus-4-7' }
          );
          if (response?.message?.content) {
            fullResponse = Array.isArray(response.message.content)
              ? response.message.content.map(p => p.text || '').join('\n')
              : response.message.content;
          } else if (typeof response === 'string') {
            fullResponse = response;
          }
        } catch (e2) {
          // Try claude-sonnet-4-6 as fallback
          const fallback = await window.puter.ai.chat(
            `${system_prompt}\n\n===\n\n${user_content}`,
            { model: 'claude-sonnet-4-6' }
          );
          fullResponse = fallback?.message?.content?.[0]?.text || fallback?.message?.content || String(fallback);
        }
      }

      if (!fullResponse || fullResponse.length < 50) {
        throw new Error('Opus returned empty response');
      }

      updateResponse(tempId, { data: { response_text: fullResponse, internal_strategy: 'Verifying citations + running Trust Layer...' } });

      // 3. Send response to backend for Trust Layer verification
      try {
        const verifyResp = await fetch(`${API}/assistant/verify-response`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          credentials: 'include',
          body: JSON.stringify({ query: queryText, response: fullResponse, sources_used: sources_used || [] }),
        });
        if (verifyResp.ok) {
          const v = await verifyResp.json();
          const finalText = v.augmented_text || fullResponse;
          updateResponse(tempId, {
            data: {
              response_text: finalText,
              models_used: ['claude-opus-4-7', 'trust-layer'],
              sections: (sources_used || []).map(s => s.title),
              internal_strategy: null,
              trust_score: v.trust_score,
              verification: v.stats,
            },
          });
        } else {
          updateResponse(tempId, { data: { response_text: fullResponse, models_used: ['claude-opus-4-7'], internal_strategy: null } });
        }
      } catch (verifyErr) {
        console.warn('Verify failed (non-blocking):', verifyErr);
        updateResponse(tempId, { data: { response_text: fullResponse, models_used: ['claude-opus-4-7'], internal_strategy: null } });
      }

      return true;
    } catch (err) {
      console.error('Opus advisory failed:', err);
      return false;
    }
  };

  const handleChatSubmit = async (queryText, tempId) => {
    // Both Quick and Partner (Deep Research) modes go through backend.
    // Backend routes: Quick → Sonnet 4.5 | Partner → Opus 4.5 (escalated if complex).
    try {
      // In dev, always use the bypass token — backend's Firebase Admin may not be configured
      // for this project, which would 401 a real Firebase idToken. DEV_TOKEN is whitelisted
      // in backend/auth_middleware.py when ENVIRONMENT != production.
      let token = '';

      try { token = await getToken() || token; } catch { /**/ }
      try { token = await getToken() || token; } catch { /**/ }
      console.log('[Spectr] Submitting query to', `${API}/assistant/query`, 'mode=', analysisMode);
      // Only include matter_id when actually set — backend declares it as required str, not Optional[str]
      const reqBody = { query: queryText, mode: analysisMode };
      if (selectedMatter) reqBody.matter_id = selectedMatter;
      // Continue an existing thread if the user clicked one in the sidebar.
      // window.__spectr_active_thread_id is set by the spectr:load-history
      // listener; handleNewThread clears it.
      if (window.__spectr_active_thread_id) reqBody.thread_id = window.__spectr_active_thread_id;
      const res = await fetch(`${API}/assistant/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        credentials: 'include',
        body: JSON.stringify(reqBody),
      }).catch(fetchErr => {
        console.error('[Spectr] fetch() threw:', fetchErr);
        throw new Error(`fetch failed: ${fetchErr.message || fetchErr}. API=${API}`);
      });
      console.log('[Spectr] Response status:', res.status, res.headers.get('content-type'));
      if (!res.ok) {
        const body = await res.text().catch(() => '');
        throw new Error(`Server ${res.status}: ${body.slice(0, 200)}`);
      }
      const contentType = res.headers.get('content-type');
      if (contentType?.includes('text/event-stream')) {
        const reader = res.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let done = false, buffer = '', currentResponse = '', currentModels = [], currentSections = [], warRoomStatus = '', partnerPayload = '';
        while (!done) {
          const { value, done: doneReading } = await reader.read();
          done = doneReading;
          if (value) {
            buffer += decoder.decode(value, { stream: true });
            const payloads = buffer.split('\n\n');
            buffer = payloads.pop() || '';
            for (const payload of payloads) {
              for (const line of payload.split('\n')) {
                if (!line.trim() || !line.startsWith('data: ')) continue;
                const dataStr = line.substring(6);
                if (dataStr === '[DONE]') { done = true; break; }
                try {
                  const parsed = JSON.parse(dataStr);
                  if (parsed.type === 'thread') {
                    // Backend emits this as the FIRST event so the client
                    // knows the thread it's writing into. Store it so
                    // follow-up messages continue this thread, and refresh
                    // the sidebar so the new title appears.
                    if (parsed.thread_id) {
                      window.__spectr_active_thread_id = parsed.thread_id;
                      window.dispatchEvent(new CustomEvent('spectr:thread-created',
                        { detail: { thread_id: parsed.thread_id } }));
                    }
                  }
                  else if (parsed.type === 'fast_chunk') currentResponse += parsed.content;
                  else if (parsed.type === 'fast_complete') { currentModels = parsed.models_used; currentSections = parsed.sections; }
                  else if (parsed.type === 'war_room_status') warRoomStatus = parsed.status;
                  else if (parsed.type === 'partner_payload') {
                    // The backend emits partner_payload TWICE for deep research:
                    //   1) initial Claude Sonnet draft
                    //   2) trust-layer augmented version with inline [\u2713]/[\u26a0] tags
                    //      (marked is_verified_version: true) \u2014 this is the SAME memo
                    //      with verification annotations, not additional content.
                    // Appending both produced the "triple memo" bug. The augmented
                    // version REPLACES the draft. Raw baseline (fast_chunk) is
                    // discarded once the deep memo arrives \u2014 we don't want two
                    // versions of the answer stacked in the UI.
                    if (parsed.is_verified_version) {
                      partnerPayload = parsed.content;   // replace, not append
                      currentResponse = '';              // drop the Groq baseline too
                    } else {
                      partnerPayload = parsed.content;   // first draft \u2014 also replace
                      currentResponse = '';
                    }
                  }
                  let fullText = currentResponse;
                  if (partnerPayload) fullText += `\n\n---\n\n${partnerPayload}`;
                  setConversations(prev => prev.map(msg => msg.id === `r_${tempId}` ? { ...msg, data: { response_text: fullText, models_used: currentModels, sections: currentSections, internal_strategy: warRoomStatus && !done ? warRoomStatus : null } } : msg));
                } catch { /**/ }
              }
            }
          }
        }
        setConversations(prev => prev.map(msg => msg.id === `r_${tempId}` ? { ...msg, isStreaming: false } : msg));
      } else {
        const data = await res.json();
        setConversations(prev => prev.map(msg => msg.id === `r_${tempId}` ? { ...msg, data, isStreaming: false } : msg));
      }
    } catch (err) {
      setConversations(prev => prev.map(msg => msg.id === `r_${tempId}` ? { ...msg, type: 'error', text: err.message, isStreaming: false } : msg));
    }
  };

  const handleToolSubmit = async (queryText, tempId) => {
    try {
      const reqBody = currentMode.buildRequest(queryText, toolParams);
      const res = await api.post(currentMode.endpoint, reqBody);
      const formatted = currentMode.formatResponse(res.data);
      setConversations(prev => prev.map(msg => msg.id === `r_${tempId}` ? { ...msg, data: { response_text: formatted }, isStreaming: false } : msg));
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || 'Tool request failed';
      setConversations(prev => prev.map(msg => msg.id === `r_${tempId}` ? { ...msg, type: 'error', text: errorMsg, isStreaming: false } : msg));
    }
  };

  const handleExport = async (format, responseText, title = 'Spectr Response') => {
    try {
      let token = '';

      try { token = await getToken() || token; } catch { /**/ }
      const endpoint = format === 'xlsx' ? 'export/excel' : format === 'docx' ? 'export/word' : 'export/pdf';
      const res = await fetch(`${API}/${endpoint}`, { method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` }, credentials: 'include', body: JSON.stringify({ content: responseText, title, format }) });
      if (!res.ok) throw new Error(`Export failed: ${res.status}`);
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href = url; a.download = `${title.replace(/\s+/g, '_')}.${format}`;
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) { console.error('Export error:', err); }
  };

  const handleCreateMatter = async () => {
    const name = prompt('Matter name:');
    if (!name) return;
    try {
      const token = (await getToken()) || '';
      const res = await fetch(`${API}/matters`, { method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` }, credentials: 'include', body: JSON.stringify({ name }) });
      if (res.ok) { const matter = await res.json(); setMatters(prev => [matter, ...prev]); setSelectedMatter(matter.matter_id); }
    } catch { /**/ }
    setShowMatterDropdown(false);
  };

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    // Task 5: accept multiple, cap at 10 total
    setAttachedFiles(prev => {
      const combined = [...prev, ...files];
      return combined.slice(0, 10);
    });
    // Keep single-file legacy state in sync (for existing tool-mode code paths)
    if (!attachedFile) setAttachedFile(files[0]);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };
  const removeAttachedFile = (idx) => {
    setAttachedFiles(prev => prev.filter((_, i) => i !== idx));
    if (attachedFiles.length === 1) setAttachedFile(null);
  };

  const handleFileSubmit = () => {
    if (!attachedFile) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target.result;
      const truncated = typeof content === 'string' ? content.substring(0, 8000) : '';
      const filePrompt = query.trim() ? `${query.trim()}\n\n[Attached: ${attachedFile.name}]\n\n${truncated}` : `Analyze this document: "${attachedFile.name}"\n\n${truncated}`;
      handleSubmit(null, filePrompt);
    };
    reader.readAsText(attachedFile);
  };

  const matterName = selectedMatter ? matters.find(m => m.matter_id === selectedMatter)?.name : null;

  const renderParamField = (param) => {
    const value = toolParams[param.key] ?? param.default ?? '';
    const fs = { padding: '6px 10px', fontSize: 12.5, border: '1px solid #E5E5E5', borderRadius: 7, outline: 'none', background: '#fff', fontFamily: "'Inter', sans-serif", color: '#111', transition: 'border-color 0.1s' };
    if (param.type === 'select') return <select key={param.key} value={value} onChange={e => updateParam(param.key, e.target.value)} style={fs}>{param.options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}</select>;
    return (
      <div key={param.key} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <span style={{ fontSize: 11.5, color: '#AAAAAA', whiteSpace: 'nowrap', fontWeight: 500 }}>{param.label}</span>
        <input type={param.type === 'date' ? 'date' : param.type} value={value} onChange={e => updateParam(param.key, e.target.value)} placeholder={param.placeholder} style={{ ...fs, width: param.type === 'number' ? 96 : param.type === 'date' ? 'auto' : 156 }} />
      </div>
    );
  };

  const getGreeting = () => {
    const h = new Date().getHours();
    const name = user?.name?.split(' ')[0] || '';
    const time = h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
    return name ? `${time}, ${name}.` : `${time}.`;
  };

  /* ─── INPUT FORM ─── */
  const renderInputForm = () => (
    <form onSubmit={(e) => { e.preventDefault(); if (attachedFile && currentMode.isChat) handleFileSubmit(); else handleSubmit(e); }}
      style={{ maxWidth: 700, margin: '0 auto', width: '100%', position: 'relative' }}>

      {/* Playbook picker — Task 9 */}
      <PlaybookPicker
        isOpen={showPlaybooks}
        searchTerm={query.startsWith('/') ? query.slice(1) : ''}
        onSelect={(pb) => {
          setSelectedPlaybook(pb);
          setQuery(pb.template || '');
          setShowPlaybooks(false);
          inputRef.current?.focus();
        }}
        onClose={() => setShowPlaybooks(false)}
      />


      {/* File chips (multi-file) */}
      {attachedFiles.length > 0 && (
        <div style={{ display: 'flex', gap: 6, marginBottom: 8, flexWrap: 'wrap' }}>
          {attachedFiles.map((f, i) => (
            <motion.div key={i}
              initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }}
              style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '5px 12px', background: 'rgba(10,10,10,0.05)', border: '1px solid rgba(10,10,10,0.1)', borderRadius: 8, fontSize: 12, color: '#444', fontWeight: 500 }}>
              <Paperclip style={{ width: 11, height: 11 }} />
              <span style={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{f.name}</span>
              <button type="button" onClick={() => removeAttachedFile(i)} style={{ background: 'none', border: 'none', padding: 0, display: 'flex' }}>
                <X style={{ width: 11, height: 11, color: '#888' }} />
              </button>
            </motion.div>
          ))}
        </div>
      )}
      {/* Playbook chip */}
      {selectedPlaybook && (
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }}
          style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '5px 12px', background: '#0A0A0A', color: '#fff', borderRadius: 8, fontSize: 12, fontWeight: 600, marginBottom: 8 }}>
          <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, opacity: 0.7 }}>/{selectedPlaybook.id}</span>
          <span>{selectedPlaybook.title}</span>
          <button type="button" onClick={() => setSelectedPlaybook(null)} style={{ background: 'none', border: 'none', padding: 0, display: 'flex', color: '#fff' }}>
            <X style={{ width: 11, height: 11 }} />
          </button>
        </motion.div>
      )}

      {/* Clean input card */}
      <div style={{
        background: '#FFFFFF',
        borderRadius: 12,
        border: '1.5px solid #E5E5E5',
        boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
        overflow: 'hidden',
        transition: 'box-shadow 0.2s, border-color 0.2s',
      }}>
        <textarea
          ref={(el) => { textareaRef.current = el; inputRef.current = el; }}
          value={query}
          onChange={e => {
            const val = e.target.value;
            setQuery(val);
            // Task 9: show playbook picker when user starts with "/"
            if (val.startsWith('/') && !val.includes(' ')) setShowPlaybooks(true);
            else setShowPlaybooks(false);
          }}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); if (attachedFile && currentMode.isChat) handleFileSubmit(); else handleSubmit(e); } }}
          onFocus={e => {
            e.currentTarget.parentElement.style.boxShadow = '0 0 0 2px rgba(0,0,0,0.08)';
            e.currentTarget.parentElement.style.borderColor = '#CCCCCC';
          }}
          onBlur={e => {
            e.currentTarget.parentElement.style.boxShadow = '0 1px 3px rgba(0,0,0,0.04)';
            e.currentTarget.parentElement.style.borderColor = '#E5E5E5';
          }}
          placeholder={clientName ? `Ask anything about ${clientName} matters...` : currentMode.placeholder}
          rows={1}
          style={{
            width: '100%', resize: 'none', background: 'transparent',
            border: 'none', outline: 'none',
            padding: '18px 22px 10px',
            fontSize: 15, color: '#111', lineHeight: 1.65,
            minHeight: 62, maxHeight: 220,
            fontFamily: "'Inter', sans-serif",
          }}
        />

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '4px 14px 12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            {/* Mode selector */}
            <div ref={modeSelectorRef} style={{ position: 'relative' }}>
              <button type="button" onClick={() => setShowModeSelector(!showModeSelector)} style={{
                display: 'flex', alignItems: 'center', gap: 5, padding: '5px 11px',
                background: activeMode !== 'assistant' ? '#0A0A0A' : 'rgba(0,0,0,0.04)',
                color: activeMode !== 'assistant' ? '#fff' : '#888',
                border: 'none', borderRadius: 8, fontSize: 12, fontWeight: 600,
                fontFamily: "'Inter', sans-serif", transition: 'all 0.15s',
              }}>
                {React.createElement(currentMode.icon, { style: { width: 11, height: 11 } })}
                {currentMode.label}
                <ChevronDown style={{ width: 9, height: 9, opacity: 0.5 }} />
              </button>

              <AnimatePresence>
                {showModeSelector && (
                  <motion.div
                    initial={{ opacity: 0, y: 8, scale: 0.97 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 8, scale: 0.97 }}
                    transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}
                    style={{
                      position: 'absolute', bottom: '110%', left: 0, width: 280,
                      background: 'rgba(255,255,255,0.98)',
                      backdropFilter: 'blur(24px)',
                      WebkitBackdropFilter: 'blur(24px)',
                      border: '1px solid rgba(0,0,0,0.08)',
                      borderRadius: 16, boxShadow: '0 20px 60px rgba(0,0,0,0.14), 0 0 0 1px rgba(0,0,0,0.04)',
                      zIndex: 50, padding: 6, maxHeight: 400, overflowY: 'auto',
                    }}
                  >
                    {MODE_CATEGORIES.map(cat => {
                      const catModes = MODES.filter(m => m.category === cat.id);
                      if (!catModes.length) return null;
                      return (
                        <div key={cat.id}>
                          <div style={{ padding: '8px 10px 4px', fontSize: 10, fontWeight: 700, color: '#BBB', letterSpacing: '.08em', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: 5 }}>
                            {React.createElement(cat.icon, { style: { width: 9, height: 9 } })}
                            {cat.label}
                          </div>
                          {catModes.map(mode => (
                            <motion.button key={mode.id} type="button"
                              whileHover={{ backgroundColor: 'rgba(0,0,0,0.04)' }}
                              whileTap={{ scale: 0.98 }}
                              onClick={() => { setActiveMode(mode.id); setToolParams({}); setShowModeSelector(false); inputRef.current?.focus(); }}
                              style={{ width: '100%', textAlign: 'left', padding: '8px 10px', background: mode.id === activeMode ? 'rgba(10,10,10,0.05)' : 'transparent', border: 'none', borderRadius: 9, display: 'flex', alignItems: 'center', gap: 10, transition: 'all 0.2s' }}>
                              <div style={{ width: 26, height: 26, borderRadius: 7, background: mode.id === activeMode ? '#0A0A0A' : '#F5F5F5', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, transition: 'all 0.3s' }}>
                                {React.createElement(mode.icon, { style: { width: 11, height: 11, color: mode.id === activeMode ? '#fff' : '#888' } })}
                              </div>
                              <div style={{ flex: 1, minWidth: 0 }}>
                                <div style={{ fontSize: 12.5, fontWeight: 600, color: '#111' }}>{mode.label}</div>
                                <div style={{ fontSize: 10.5, color: '#AAA', marginTop: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{mode.description}</div>
                              </div>
                              {mode.id === activeMode && <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#0A0A0A', flexShrink: 0 }} />}
                            </motion.button>
                          ))}
                        </div>
                      );
                    })}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* File attach */}
            <input ref={fileInputRef} type="file" multiple accept=".pdf,.docx,.doc,.txt,.xlsx,.csv,.json" onChange={handleFileSelect} style={{ display: 'none' }} />
            <button type="button" onClick={() => fileInputRef.current?.click()} style={{ width: 30, height: 30, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'none', border: 'none', borderRadius: 7, color: '#CCC', transition: 'color 0.1s' }}
              onMouseEnter={e => e.currentTarget.style.color = '#777'}
              onMouseLeave={e => e.currentTarget.style.color = '#CCC'}>
              <Paperclip style={{ width: 13, height: 13 }} />
            </button>
          </div>

          {/* Send button */}
          <button type="submit" disabled={(!query.trim() && !attachedFile) || loading}
            className="send-btn"
            style={{
              width: 38, height: 38, display: 'flex', alignItems: 'center', justifyContent: 'center',
              borderRadius: '50%', border: 'none',
              background: (query.trim() || attachedFile) && !loading
                ? '#0A0A0A'
                : 'rgba(0,0,0,0.06)',
              color: (query.trim() || attachedFile) && !loading ? '#fff' : '#C8C8C8',
              boxShadow: (query.trim() || attachedFile) && !loading ? '0 4px 12px rgba(0,0,0,0.15)' : 'none',
              transition: 'all 0.2s cubic-bezier(0.16,1,0.3,1)',
            }}
            onMouseEnter={e => { if ((query.trim() || attachedFile) && !loading) { e.currentTarget.style.transform = 'scale(1.1)'; e.currentTarget.style.boxShadow = '0 6px 20px rgba(0,0,0,0.25)'; } }}
            onMouseLeave={e => { e.currentTarget.style.transform = 'scale(1)'; e.currentTarget.style.boxShadow = (query.trim() || attachedFile) && !loading ? '0 4px 12px rgba(0,0,0,0.15)' : 'none'; }}>
            {loading
              ? <Loader2 style={{ width: 14, height: 14, animation: 'spin 0.8s linear infinite' }} />
              : <ArrowUp style={{ width: 16, height: 16 }} />}
          </button>
        </div>
      </div>

      {currentMode.params && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', padding: '9px 2px 0' }}>
          {currentMode.params.map(renderParamField)}
        </div>
      )}
    </form>
  );

  /* ─── RENDER ─── */
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: '#FFFFFF', fontFamily: "'Inter', sans-serif", letterSpacing: '-0.02em', position: 'relative', overflow: 'hidden', WebkitFontSmoothing: 'antialiased' }}>

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,200..800;1,200..800&family=Instrument+Serif:ital@0;1&display=swap');
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes greetIn { from { opacity:0; transform:translateY(60px) scale(0.96); } to { opacity:1; transform:translateY(0) scale(1); } }
        @keyframes chipIn { from { opacity:0; transform:translateY(24px) scale(0.9); } to { opacity:1; transform:translateY(0) scale(1); } }
        @keyframes popUp { from { opacity:0; transform:translateY(8px) scale(0.97); } to { opacity:1; transform:translateY(0) scale(1); } }
        @keyframes msgSlide { from { opacity:0; transform:translateY(14px); } to { opacity:1; transform:translateY(0); } }
        @keyframes orbFloat1 { 0%,100% { transform:translateY(0px) scale(1); } 50% { transform:translateY(-20px) scale(1.04); } }
        @keyframes orbFloat2 { 0%,100% { transform:translateY(0px) scale(1); } 50% { transform:translateY(-14px) scale(1.02); } }
        @keyframes typingBounce { 0%,60%,100% { transform:translateY(0); opacity:0.35; } 30% { transform:translateY(-6px); opacity:1; } }
        @keyframes shimmer { 0% { opacity:0.6; } 50% { opacity:1; } 100% { opacity:0.6; } }

        .msg-user-bubble {
          background: linear-gradient(135deg, #0A0A0A, #1A1A1A);
          color: #fff; border-radius: 18px 18px 4px 18px;
          padding: 13px 18px; max-width: 68%;
          box-shadow: 0 4px 16px rgba(0,0,0,0.18), 0 1px 4px rgba(0,0,0,0.1);
          animation: msgSlide 0.3s cubic-bezier(0.16,1,0.3,1) both;
        }
        .msg-ai-wrap { animation: msgSlide 0.35s cubic-bezier(0.16,1,0.3,1) both; }

        .ai-avatar-ring {
          animation: shimmer 2s ease-in-out infinite;
        }

        .thread-mode-btn {
          font-size: 11.5px; font-weight: 600; padding: 3px 12px;
          border-radius: 6px; border: none;
          transition: all 0.3s cubic-bezier(0.16,1,0.3,1); font-family: 'Inter', sans-serif;
        }
        .thread-mode-btn:active { transform: scale(0.96); }

        @keyframes fadeInUp { from { opacity:0; transform:translateY(16px); } to { opacity:1; transform:translateY(0); } }
        @keyframes scaleIn { from { opacity:0; transform:scale(0.95); } to { opacity:1; transform:scale(1); } }
        @keyframes slideInRight { from { opacity:0; transform:translateX(20px); } to { opacity:1; transform:translateX(0); } }
        @keyframes pulseGlow { 0%,100% { box-shadow: 0 0 0 0 rgba(10,10,10,0.08); } 50% { box-shadow: 0 0 20px 4px rgba(10,10,10,0.06); } }
        @keyframes breathe { 0%,100% { opacity:0.4; } 50% { opacity:1; } }

        .msg-user-bubble {
          background: linear-gradient(135deg, #0A0A0A, #1A1A1A);
          color: #fff; border-radius: 18px 18px 4px 18px;
          padding: 13px 18px; max-width: 68%;
          box-shadow: 0 4px 16px rgba(0,0,0,0.18), 0 1px 4px rgba(0,0,0,0.1);
          animation: slideInRight 0.4s cubic-bezier(0.16,1,0.3,1) both;
          transition: transform 0.3s cubic-bezier(0.16,1,0.3,1);
        }
        .msg-user-bubble:hover { transform: scale(1.01); }
        .msg-ai-wrap { animation: fadeInUp 0.45s cubic-bezier(0.16,1,0.3,1) both; }

        .ai-avatar-ring { animation: pulseGlow 3s ease-in-out infinite; }

        .suggest-card {
          transition: all 0.4s cubic-bezier(0.16,1,0.3,1);
        }
        .suggest-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 8px 24px rgba(0,0,0,0.06);
          border-color: #0A0A0A !important;
        }
        .suggest-card:active { transform: scale(0.98); transition: all 0.1s; }

        .action-pill {
          transition: all 0.4s cubic-bezier(0.16,1,0.3,1);
        }
        .action-pill:hover {
          border-color: #0A0A0A; color: #0A0A0A;
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(0,0,0,0.06);
        }
        .action-pill:active { transform: scale(0.96); transition: all 0.1s; }

        .send-btn {
          transition: all 0.3s cubic-bezier(0.16,1,0.3,1);
          box-shadow: 0 2px 8px rgba(0,0,0,0.15), inset 0 1px 0 rgba(255,255,255,0.1);
        }
        .send-btn:hover { transform: scale(1.08); box-shadow: 0 6px 20px rgba(0,0,0,0.25), inset 0 1px 0 rgba(255,255,255,0.15); }
        .send-btn:active { transform: scale(0.92); transition: all 0.1s; box-shadow: inset 0 2px 4px rgba(0,0,0,0.3); }

        .pill-btn {
          transition: all 0.4s cubic-bezier(0.16,1,0.3,1);
          box-shadow: 0 1px 2px rgba(0,0,0,0.04), inset 0 1px 0 rgba(255,255,255,0.5);
        }
        .pill-btn:hover {
          border-color: #0A0A0A; color: #0A0A0A;
          transform: translateY(-2px);
          box-shadow: 0 6px 20px rgba(0,0,0,0.06), inset 0 1px 0 rgba(255,255,255,0.6);
        }
        .pill-btn:active { transform: scale(0.97); transition: all 0.1s; box-shadow: inset 0 1px 3px rgba(0,0,0,0.08); }

        .source-pill {
          transition: all 0.3s cubic-bezier(0.16,1,0.3,1);
        }
        .source-pill:hover { border-color: #CCC; background: rgba(0,0,0,0.02); transform: translateY(-1px); }

        .recent-item {
          transition: all 0.3s cubic-bezier(0.16,1,0.3,1);
        }
        .recent-item:hover { background: #FAFAFA; padding-left: 10px; }
      `}</style>

      {/* ─── EMPTY STATE — Harvey-style centered layout ─── */}
      {!hasConversations && (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '32px 40px 40px', overflow: 'auto' }}>
          <div style={{ width: '100%', maxWidth: 680, margin: '0 auto', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>

            {/* Big centered Blaxel wordmark — Spectr */}
            <motion.h1
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
              style={{
                fontFamily: "'Inter', sans-serif",
                fontSize: 56, fontWeight: 500,
                background: 'linear-gradient(to bottom right, #0A0A0A 40%, rgba(10,10,10,0.45))',
                WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
                backgroundClip: 'text',
                textAlign: 'center', letterSpacing: '-0.055em',
                lineHeight: 1, margin: '0 0 24px',
              }}
            >Spectr</motion.h1>

            {/* Quick action chips — Draft / Review */}
            <motion.div
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.12, duration: 0.4 }}
              style={{ display: 'flex', gap: 10, marginBottom: 28, justifyContent: 'center' }}
            >
              {[
                { label: 'Draft document', icon: FileText, onClick: () => { setQuery('Draft a '); inputRef.current?.focus(); } },
                { label: 'Review document', icon: FileCheck, onClick: () => { fileInputRef.current?.click(); } },
              ].map((b, i) => (
                <button key={i} onClick={b.onClick}
                  style={{
                    display: 'inline-flex', alignItems: 'center', gap: 7,
                    padding: '8px 16px', background: '#FFFFFF',
                    border: '1px solid rgba(0,0,0,0.08)', borderRadius: 999,
                    fontSize: 13, fontWeight: 500, color: '#0A0A0A',
                    fontFamily: "'Inter', sans-serif", letterSpacing: '-0.01em',
                    cursor: 'pointer', transition: 'all 0.15s',
                  }}
                  onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(0,0,0,0.18)'; e.currentTarget.style.background = '#FAFAFA'; }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(0,0,0,0.08)'; e.currentTarget.style.background = '#FFFFFF'; }}
                >
                  <b.icon style={{ width: 13, height: 13, strokeWidth: 1.8, opacity: 0.7 }} />
                  {b.label}
                </button>
              ))}
            </motion.div>

            {/* Starter prompts — legal-specific showcase queries */}
            <motion.div
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.18, duration: 0.4 }}
              style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'center', marginBottom: 28, maxWidth: 700 }}
            >
              {[
                { label: 'GST SCN — Section 74 reply', prompt: 'Client received SCN under Section 74 CGST Act for ₹48 lakh ITC mismatch for FY 2019-20. SCN issued on 2 January 2025. Supplier filed GSTR-1; client filed GSTR-3B on time. Draft our complete reply strategy covering limitation, ITC entitlement, and natural justice.' },
                { label: 'DPDP — Right to be Forgotten challenge', prompt: 'Client acquitted 12 years ago approaches us to erase his judicial records from NJDG and IndianKanoon under DPDP Section 12(3). Draft our opinion on maintainability and the current Supreme Court position after July 2024 and SLP(C) 4054/2026 stays.' },
                { label: 'Bail — BNS S.318 cheating', prompt: 'Our client arrested under BNS S.318 (cheating) 40 days ago. First-time offender, fixed address, no prior record. Mumbai Sessions Court. Draft a bail application with BNSS S.483 framework and cite the strongest Bombay HC precedents on first-time economic offenders.' },
                { label: 'Constitutional — Aadhaar-linked rule', prompt: 'Union notification mandates Aadhaar-based biometric verification for all social media users with over 50,000 followers. Draft our writ challenging this under Article 14, 19(1)(a), 21, citing Puttaswamy II and recent SC stays.' },
              ].map((p, i) => (
                <button key={i}
                  onClick={() => {
                    setQuery(p.prompt);
                    inputRef.current?.focus();
                  }}
                  style={{
                    padding: '9px 14px', background: '#FAFAFA',
                    border: '1px solid rgba(0,0,0,0.06)', borderRadius: 10,
                    fontSize: 12, fontWeight: 500, color: '#4B5563',
                    fontFamily: "'Inter', sans-serif", letterSpacing: '-0.01em',
                    cursor: 'pointer', transition: 'all 0.15s',
                    textAlign: 'left', maxWidth: 320,
                  }}
                  onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(0,0,0,0.18)'; e.currentTarget.style.background = '#FFFFFF'; e.currentTarget.style.color = '#0A0A0A'; }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(0,0,0,0.06)'; e.currentTarget.style.background = '#FAFAFA'; e.currentTarget.style.color = '#4B5563'; }}
                  title={p.prompt.substring(0, 150) + '...'}
                >
                  {p.label}
                </button>
              ))}
            </motion.div>

            {/* ── Centered input — Harvey style ── */}
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.22, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
              style={{ width: '100%' }}
            >
              {/* Flanking row: Client matter ↔ Research mode */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10, padding: '0 4px' }}>
                <div ref={matterRef} style={{ position: 'relative' }}>
                  <button onClick={() => setShowMatterDropdown(!showMatterDropdown)} style={{ display: 'flex', alignItems: 'center', gap: 4, background: 'none', border: 'none', fontSize: 13, color: matterName ? '#222' : '#AAA', fontWeight: 500, cursor: 'pointer', padding: '4px 0', fontFamily: "'Inter', sans-serif", letterSpacing: '-0.01em' }}>
                    {matterName || 'Client matter'} <ChevronDown style={{ width: 10, height: 10, opacity: 0.4 }} />
                  </button>
                  {showMatterDropdown && (
                    <motion.div initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.15 }}
                      style={{ position: 'absolute', top: '120%', left: 0, width: 220, background: '#fff', border: '1px solid rgba(0,0,0,0.08)', borderRadius: 12, boxShadow: '0 12px 40px rgba(0,0,0,0.1)', zIndex: 50, padding: 4 }}>
                      <button onClick={() => { setSelectedMatter(''); setShowMatterDropdown(false); }} style={{ width: '100%', textAlign: 'left', padding: '8px 10px', fontSize: 13, color: '#888', background: 'none', border: 'none', borderRadius: 8, fontFamily: 'inherit' }} onMouseEnter={e => e.currentTarget.style.background='#F7F7F7'} onMouseLeave={e => e.currentTarget.style.background='none'}>No matter</button>
                      {matters.map(m => (
                        <button key={m.matter_id} onClick={() => { setSelectedMatter(m.matter_id); setShowMatterDropdown(false); }} style={{ width: '100%', textAlign: 'left', padding: '8px 10px', fontSize: 13, color: '#111', fontWeight: 500, background: 'none', border: 'none', borderRadius: 8, fontFamily: 'inherit' }} onMouseEnter={e => e.currentTarget.style.background='#F7F7F7'} onMouseLeave={e => e.currentTarget.style.background='none'}>{m.name}</button>
                      ))}
                      <div style={{ height: 1, background: '#F0F0F0', margin: '3px 8px' }} />
                      <button onClick={handleCreateMatter} style={{ width: '100%', textAlign: 'left', padding: '8px 10px', fontSize: 13, color: '#111', fontWeight: 600, background: 'none', border: 'none', borderRadius: 8, display: 'flex', alignItems: 'center', gap: 6, fontFamily: 'inherit' }} onMouseEnter={e => e.currentTarget.style.background='#F7F7F7'} onMouseLeave={e => e.currentTarget.style.background='none'}><Plus style={{ width: 11, height: 11 }} /> New matter</button>
                    </motion.div>
                  )}
                </div>
                {/* Mode toggle removed — Groq orchestrator picks the model per query */}
              </div>

              {/* Main input */}
              {renderInputForm()}
            </motion.div>

            {/* Integration pills row — Harvey style (Vault / IndianKanoon / GST / Drive) */}
            <motion.div
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4, duration: 0.4 }}
              style={{ display: 'flex', gap: 10, justifyContent: 'center', flexWrap: 'wrap', marginTop: 18 }}
            >
              {[
                { id: 'vault', label: 'Vault', icon: FolderOpen, onClick: () => nav('/app/vault') },
                { id: 'ik', label: 'IndianKanoon', icon: Scale, onClick: () => nav('/app/caselaw') },
                { id: 'gst', label: 'GST Returns', icon: Receipt, onClick: () => { setActiveMode('penalty'); inputRef.current?.focus(); } },
                { id: 'drive', label: 'Drive', icon: FolderOpen, onClick: () => nav('/app/vault') },
              ].map(p => (
                <button key={p.id} onClick={p.onClick}
                  style={{
                    display: 'inline-flex', alignItems: 'center', gap: 7,
                    padding: '6px 13px', background: '#FFFFFF',
                    border: '1px solid rgba(0,0,0,0.07)', borderRadius: 999,
                    fontSize: 12, fontWeight: 500, color: '#555',
                    fontFamily: "'Inter', sans-serif", letterSpacing: '-0.01em',
                    cursor: 'pointer', transition: 'all 0.15s',
                  }}
                  onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(0,0,0,0.16)'; e.currentTarget.style.color = '#0A0A0A'; }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(0,0,0,0.07)'; e.currentTarget.style.color = '#555'; }}
                >
                  <p.icon style={{ width: 12, height: 12, strokeWidth: 1.8, opacity: 0.7 }} />
                  {p.label}
                  <Plus style={{ width: 10, height: 10, opacity: 0.4, marginLeft: 2 }} />
                </button>
              ))}
            </motion.div>

            {/* Browse workflows link */}
            <motion.button
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.55, duration: 0.4 }}
              onClick={() => nav('/app/workflows')}
              style={{
                marginTop: 24, background: 'none', border: 'none', cursor: 'pointer',
                fontSize: 12, color: '#AAA', fontWeight: 500,
                fontFamily: "'Inter', sans-serif", letterSpacing: '-0.005em',
                display: 'inline-flex', alignItems: 'center', gap: 5,
                transition: 'color 0.15s',
              }}
              whileHover={{ color: '#0A0A0A' }}
            >
              Browse 38 workflows
              <ArrowRight style={{ width: 11, height: 11 }} />
            </motion.button>
          </div>
        </div>
      )}

      {/* ─── CONVERSATION STATE ─── */}
      {hasConversations && (
        <>
          {/* Thread bar */}
          <div style={{
            height: 48, display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '0 32px', flexShrink: 0,
            background: 'rgba(255,255,255,0.8)',
            backdropFilter: 'blur(12px)',
            WebkitBackdropFilter: 'blur(12px)',
            borderBottom: '1px solid rgba(0,0,0,0.05)',
          }}>
            <div ref={matterRef} style={{ position: 'relative', display: 'flex', alignItems: 'center', gap: 4 }}>
              {/* New thread — actually starts a fresh conversation */}
              <button onClick={handleNewThread} title="Start new thread" style={{
                display: 'flex', alignItems: 'center', gap: 6, padding: '5px 10px',
                background: 'none', border: '1px solid transparent', borderRadius: 7,
                fontSize: 13, fontWeight: 500, color: '#555',
                fontFamily: "'Inter', sans-serif", cursor: 'pointer',
                transition: 'all 0.15s',
              }}
                onMouseEnter={e => { e.currentTarget.style.background = '#F5F5F5'; e.currentTarget.style.color = '#0A0A0A'; }}
                onMouseLeave={e => { e.currentTarget.style.background = 'none'; e.currentTarget.style.color = '#555'; }}
              >
                <Plus style={{ width: 12, height: 12, strokeWidth: 2.2 }} />
                New thread
              </button>
              {/* Matter chooser — separate dropdown, only visible when matter is set */}
              {matterName && (
                <button onClick={() => setShowMatterDropdown(!showMatterDropdown)} style={{
                  display: 'flex', alignItems: 'center', gap: 6, padding: '5px 10px',
                  background: 'rgba(10,10,10,0.04)', border: '1px solid rgba(0,0,0,0.06)', borderRadius: 7,
                  fontSize: 13, fontWeight: 500, color: '#222',
                  fontFamily: "'Inter', sans-serif", cursor: 'pointer',
                }}>
                  <FileText style={{ width: 11, height: 11, opacity: 0.5 }} />
                  {matterName}
                  <ChevronDown style={{ width: 9, height: 9, opacity: 0.35 }} />
                </button>
              )}
              {showMatterDropdown && (
                <div style={{ position: 'absolute', top: '115%', left: 0, width: 232, background: 'rgba(255,255,255,0.96)', backdropFilter: 'blur(16px)', border: '1px solid rgba(0,0,0,0.06)', borderRadius: 12, boxShadow: '0 8px 32px rgba(0,0,0,0.1)', zIndex: 50, padding: 4, animation: 'popUp 0.14s ease-out' }}>
                  <button onClick={() => { setSelectedMatter(''); setShowMatterDropdown(false); }} style={{ width: '100%', textAlign: 'left', padding: '8px 11px', fontSize: 13, color: '#888', background: 'none', border: 'none', borderRadius: 8, fontFamily: 'inherit' }} onMouseEnter={e => e.currentTarget.style.background = '#F7F7F7'} onMouseLeave={e => e.currentTarget.style.background = 'none'}>New thread</button>
                  {matters.map(m => (
                    <button key={m.matter_id} onClick={() => { setSelectedMatter(m.matter_id); setShowMatterDropdown(false); }} style={{ width: '100%', textAlign: 'left', padding: '8px 11px', fontSize: 13, color: '#111', background: 'none', border: 'none', borderRadius: 8, fontWeight: 500, fontFamily: 'inherit' }} onMouseEnter={e => e.currentTarget.style.background = '#F7F7F7'} onMouseLeave={e => e.currentTarget.style.background = 'none'}>{m.name}</button>
                  ))}
                  <div style={{ height: 1, background: '#F0F0F0', margin: '3px 8px' }} />
                  <button onClick={handleCreateMatter} style={{ width: '100%', textAlign: 'left', padding: '8px 11px', fontSize: 13, color: '#111', fontWeight: 600, background: 'none', border: 'none', borderRadius: 8, display: 'flex', alignItems: 'center', gap: 6, fontFamily: 'inherit' }} onMouseEnter={e => e.currentTarget.style.background = '#F7F7F7'} onMouseLeave={e => e.currentTarget.style.background = 'none'}><Plus style={{ width: 12, height: 12 }} /> New matter</button>
                </div>
              )}
            </div>

            {/* Research mode dropdown removed — Groq orchestrator picks the model per query */}
          </div>

          {/* Messages */}
          <div style={{ flex: 1, overflowY: 'auto', background: '#FFFFFF' }}>
            <div style={{ padding: '40px 48px 0', maxWidth: 860, margin: '0 auto' }}>
              {conversations.map((conv, i) => {
                if (conv.type === 'query') return (
                  <div key={conv.id} style={{ display: 'flex', justifyContent: 'flex-end', margin: '0 0 10px' }}>
                    <div className="msg-user-bubble">
                      <p style={{ fontSize: 14.5, color: '#fff', margin: 0, lineHeight: 1.62, whiteSpace: 'pre-wrap', fontFamily: "'Inter', sans-serif" }}>{conv.text}</p>
                    </div>
                  </div>
                );

                if (conv.type === 'response') return (
                  <div key={conv.id} className="msg-ai-wrap" style={{ margin: '10px 0 36px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
                      <div className="ai-avatar-ring" style={{
                        width: 28, height: 28, borderRadius: 9, flexShrink: 0,
                        background: 'linear-gradient(135deg, #0A0A0A, #1A1A1A)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        boxShadow: '0 2px 8px rgba(0,0,0,0.2), 0 0 0 2px rgba(0,0,0,0.1)',
                      }}>
                        <Scale style={{ width: 12, height: 12, color: '#0A0A0A', strokeWidth: 1.8 }} />
                      </div>
                      <span style={{
                        fontFamily: "'Inter', sans-serif", fontSize: 15, fontWeight: 500,
                        background: 'linear-gradient(to bottom right, #0A0A0A 40%, rgba(10,10,10,0.45))',
                        WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
                        backgroundClip: 'text',
                        letterSpacing: '-0.05em',
                      }}>Spectr</span>
                      {/* Trust badge — Task 8 */}
                      {conv.data.trust_score != null && (
                        <TrustScoreBadge
                          trustScore={conv.data.trust_score}
                          stats={conv.data.verification}
                          verificationReport={conv.data.verification_report}
                          notes={conv.data.notes}
                        />
                      )}
                    </div>
                    <div style={{ paddingLeft: 38 }}>
                      <ResponseCard
                        responseText={conv.data.response_text} sections={conv.data.sections}
                        sources={conv.data.sources} modelUsed={conv.data.model_used}
                        citationsCount={conv.data.citations_count} internalStrategy={conv.data.internal_strategy}
                        onExport={(format) => handleExport(format, conv.data.response_text)}
                        onDraft={() => { setQuery(`Draft a formal document based on: ${conversations[i - 1]?.text || 'the previous analysis'}`); inputRef.current?.focus(); }}
                        onSmartAction={(prompt) => handleSubmit(null, prompt)}
                      />
                      {/* Generated files — Drive upload + Edit buttons (Task 2 + 6) */}
                      {conv.data.download_urls?.length > 0 && (
                        <div style={{ marginTop: 14, padding: '12px 14px', background: '#FAFAFA', border: '1px solid #EBEBEB', borderRadius: 10 }}>
                          <div style={{ fontSize: 10, fontWeight: 700, color: '#AAA', letterSpacing: '.06em', textTransform: 'uppercase', marginBottom: 10 }}>
                            Generated files
                          </div>
                          {conv.data.download_urls.map((f, fi) => (
                            <div key={fi} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '6px 0', borderTop: fi > 0 ? '1px solid #F0F0F0' : 'none' }}>
                              <FileText style={{ width: 13, height: 13, color: '#888', flexShrink: 0 }} />
                              <div style={{ flex: 1, minWidth: 0 }}>
                                <div style={{ fontSize: 13, fontWeight: 600, color: '#222', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{f.name}</div>
                                {f.size && <div style={{ fontSize: 10.5, color: '#AAA', marginTop: 1 }}>{(f.size / 1024).toFixed(1)} KB</div>}
                              </div>
                              <a href={f.url?.startsWith('http') ? f.url : `${API}${f.url}`} download={f.name}
                                style={{ fontSize: 11, padding: '5px 10px', background: '#fff', border: '1px solid #E5E5E5', borderRadius: 7, color: '#444', textDecoration: 'none', fontWeight: 600 }}>
                                Download
                              </a>
                              <DriveUploadButton fileId={f.file_id} fileName={f.name} />
                              <button
                                onClick={() => { setLastGeneratedFile(f); setQuery(`Modify the file "${f.name}": `); inputRef.current?.focus(); }}
                                style={{ fontSize: 11, padding: '5px 10px', background: '#fff', border: '1px solid #E5E5E5', borderRadius: 7, color: '#444', fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit' }}>
                                Edit
                              </button>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                );

                if (conv.type === 'error') return (
                  <div key={conv.id} style={{ display: 'flex', alignItems: 'flex-start', gap: 10, padding: '12px 16px', margin: '0 0 18px', border: '1px solid rgba(239,68,68,0.12)', borderRadius: 12, background: 'rgba(239,68,68,0.04)', animation: 'msgSlide 0.22s ease-out' }}>
                    <div style={{ width: 5, height: 5, borderRadius: '50%', background: '#EF4444', marginTop: 8, flexShrink: 0 }} />
                    <div style={{ flex: 1 }}>
                      <p style={{ fontSize: 13.5, color: '#999', margin: '0 0 8px', lineHeight: 1.6 }}>
                        {conv.text?.includes('fetch') || conv.text?.includes('network') ? 'Connection issue. Check your network and retry.' : conv.text?.includes('500') || conv.text?.includes('503') ? 'The AI is momentarily busy — please try again.' : 'Something went wrong. Please try again.'}
                      </p>
                      {conv.text && (
                        <p style={{ fontSize: 11, color: '#BBB', margin: '0 0 8px', lineHeight: 1.5, fontFamily: 'monospace', wordBreak: 'break-word' }}>
                          Debug: {conv.text}
                        </p>
                      )}
                      <button onClick={() => setConversations(prev => prev.filter(c => !c.id.endsWith(conv.id.split('_')[1])))}
                        style={{ fontSize: 12, fontWeight: 500, color: '#CCC', background: 'none', border: '1px solid #EBEBEB', borderRadius: 6, padding: '4px 12px', fontFamily: "'Inter', sans-serif" }}
                        onMouseEnter={e => { e.currentTarget.style.color = '#666'; e.currentTarget.style.borderColor = '#CCC'; }}
                        onMouseLeave={e => { e.currentTarget.style.color = '#CCC'; e.currentTarget.style.borderColor = '#EBEBEB'; }}>Dismiss</button>
                    </div>
                  </div>
                );
                return null;
              })}

              {/* Minimal typing dots for triage (greetings/casual) — no fake pipeline */}
              {loading && currentMode.isChat && isTriageLoading && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.25 }}
                  style={{ margin: '10px 0 36px' }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
                    <div style={{
                      width: 28, height: 28, borderRadius: 9,
                      background: 'linear-gradient(135deg, #0A0A0A, #1A1A1A)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}>
                      <Scale style={{ width: 12, height: 12, color: '#fff', strokeWidth: 1.8 }} />
                    </div>
                    <span style={{ fontFamily: "'Inter', sans-serif", fontSize: 14, fontWeight: 700, color: '#0A0A0A' }}>Spectr</span>
                  </div>
                  <div style={{ paddingLeft: 38, display: 'flex', alignItems: 'center', gap: 5 }}>
                    {[0, 1, 2].map(i => (
                      <motion.span key={i}
                        animate={{ opacity: [0.25, 1, 0.25], y: [0, -3, 0] }}
                        transition={{ duration: 1.1, repeat: Infinity, delay: i * 0.18, ease: 'easeInOut' }}
                        style={{ width: 5, height: 5, borderRadius: '50%', background: '#0A0A0A', display: 'inline-block' }}
                      />
                    ))}
                  </div>
                </motion.div>
              )}

              {/* Full research pipeline indicator — only for actual legal queries */}
              {loading && currentMode.isChat && !isTriageLoading && (
                <motion.div
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
                  style={{ margin: '10px 0 36px' }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
                    <div style={{
                      width: 28, height: 28, borderRadius: 9,
                      background: 'linear-gradient(135deg, #0A0A0A, #1A1A1A)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      boxShadow: '0 2px 8px rgba(0,0,0,0.2), 0 0 0 2px rgba(0,0,0,0.08)',
                    }}>
                      <Scale style={{ width: 12, height: 12, color: '#fff', strokeWidth: 1.8 }} />
                    </div>
                    <span style={{
                      fontFamily: "'Inter', sans-serif", fontSize: 15, fontWeight: 500,
                      background: 'linear-gradient(to bottom right, #0A0A0A 40%, rgba(10,10,10,0.45))',
                      WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
                      backgroundClip: 'text',
                      letterSpacing: '-0.05em',
                    }}>Spectr</span>
                    <span style={{ fontSize: 11, color: '#BBB', fontWeight: 500 }}>
                      {analysisMode === 'everyday' ? 'Quick' : analysisMode === 'research' ? 'Deep Research' : 'Depth Research'}
                    </span>
                  </div>
                  <div style={{ paddingLeft: 38 }}>
                    {/* 3D Cube Loader */}
                    <div style={{
                      display: 'inline-flex', alignItems: 'center', gap: 16, padding: '14px 20px',
                      background: '#FAFAFA',
                      border: '1px solid rgba(0,0,0,0.06)',
                      borderRadius: '6px 16px 16px 16px',
                      boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
                      marginBottom: 16, minHeight: 52,
                    }}>
                      <CubeLoader size={0.22} />
                      <div style={{ marginLeft: 16 }}>
                        <div style={{ fontSize: 12.5, fontWeight: 600, color: '#333', marginBottom: 2, fontFamily: "'Inter', sans-serif" }}>
                          {THINKING_STEPS[thinkingStep] || 'Thinking...'}
                        </div>
                        <div style={{ fontSize: 11, color: '#BBB' }}>
                          Step {thinkingStep + 1} of {THINKING_STEPS.length}
                        </div>
                      </div>
                    </div>
                    {/* Step progress */}
                    <div style={{ display: 'flex', gap: 3, marginBottom: 12, paddingLeft: 2 }}>
                      {THINKING_STEPS.map((_, idx) => (
                        <motion.div key={idx}
                          initial={{ scaleX: 0 }}
                          animate={{ scaleX: idx <= thinkingStep ? 1 : 0 }}
                          transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
                          style={{
                            width: `${100 / THINKING_STEPS.length}%`, height: 2, borderRadius: 1,
                            background: idx <= thinkingStep ? '#0A0A0A' : '#EBEBEB',
                            transformOrigin: 'left',
                            transition: 'background 0.3s',
                          }}
                        />
                      ))}
                    </div>
                    {/* Recent steps */}
                    {THINKING_STEPS.slice(Math.max(0, thinkingStep - 2), thinkingStep + 1).map((step, idx, arr) => {
                      const isActive = idx === arr.length - 1;
                      return (
                        <motion.div key={step}
                          initial={{ opacity: 0, x: -6 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ duration: 0.3 }}
                          style={{ fontSize: 11.5, color: isActive ? '#666' : '#CCC', display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4, fontFamily: "'Inter', sans-serif" }}>
                          <span style={{ width: 4, height: 4, borderRadius: '50%', background: isActive ? '#0A0A0A' : '#DDD', flexShrink: 0 }} />
                          {step}
                        </motion.div>
                      );
                    })}
                  </div>
                </motion.div>
              )}

              {loading && !currentMode.isChat && (
                <div style={{ margin: '14px 0', display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Loader2 style={{ width: 13, height: 13, animation: 'spin 0.8s linear infinite', color: '#AAAAAA' }} />
                  <span style={{ fontSize: 13.5, color: '#AAAAAA', fontFamily: "'Inter', sans-serif" }}>Processing...</span>
                </div>
              )}
              <div ref={responseEndRef} style={{ height: 28 }} />
            </div>
          </div>

          {/* Bottom input */}
          <div style={{
            padding: '12px 48px 24px', flexShrink: 0,
            background: 'rgba(250,250,250,0.9)',
            backdropFilter: 'blur(12px)',
            WebkitBackdropFilter: 'blur(12px)',
            borderTop: '1px solid rgba(0,0,0,0.04)',
          }}>
            {renderInputForm()}
          </div>
        </>
      )}
    </div>
  );
}
