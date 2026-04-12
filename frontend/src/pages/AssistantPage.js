import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import ResponseCard from '../components/ResponseCard';
import api from '../services/api';
import {
  Plus, FileText, Loader2,
  Paperclip, ArrowUp, X, ChevronDown, Scale, ArrowRight
} from 'lucide-react';

const display = "'Plus Jakarta Sans', 'Inter', sans-serif";

const API = process.env.NODE_ENV === 'development' ? 'http://localhost:8000/api' : '/api';

/* ──────────────────────────────────────────────
   Tool modes — each one turns the chat input into
   a specialised tool. "assistant" is the default
   general-purpose AI chat with SSE streaming.
   ────────────────────────────────────────────── */
const MODES = [
  {
    id: 'assistant',
    label: 'Assistant',
    description: 'Legal & tax AI',
    placeholder: 'Ask anything about Indian law and tax...',
    isChat: true,
  },
  {
    id: 'tds',
    label: 'TDS Classifier',
    description: 'Detect section & rate',
    placeholder: 'Describe the payment...',
    endpoint: '/tools/tds-classifier',
    params: [
      { key: 'amount', label: 'Amount (₹)', type: 'number', placeholder: '100000' },
      { key: 'payee_type', label: 'Payee', type: 'select', default: 'individual', options: [
        { value: 'individual', label: 'Individual / HUF' },
        { value: 'company', label: 'Company' },
        { value: 'firm', label: 'Firm' },
      ]},
    ],
    buildRequest: (query, p) => ({
      description: query,
      amount: parseFloat(p.amount) || 0,
      payee_type: p.payee_type || 'individual',
      is_non_filer: false,
    }),
    formatResponse: (d) => {
      if (d.error) return d.error;
      return `## Section ${d.section}\n**${d.title}**\n\n| Parameter | Value |\n|---|---|\n| Rate | ${d.rate_percent ?? d.rate}% |\n| Threshold | ₹${d.threshold?.toLocaleString('en-IN') || 'N/A'} |\n| TDS Amount | ₹${d.tds_amount?.toLocaleString('en-IN') || 'N/A'} |${d.note ? '\n\n> ' + d.note : ''}`;
    },
  },
  {
    id: 'penalty',
    label: 'Penalty Calc',
    description: 'Late filing penalties',
    placeholder: 'Notes (optional)...',
    endpoint: '/tools/penalty-calculator',
    params: [
      { key: 'deadline_type', label: 'Type', type: 'select', default: 'gstr3b', options: [
        { value: 'gstr3b', label: 'GSTR-3B' },
        { value: 'gstr1', label: 'GSTR-1' },
        { value: 'gstr9', label: 'GSTR-9' },
        { value: 'itr', label: 'ITR' },
        { value: 'tds_return', label: 'TDS Return' },
        { value: 'roc', label: 'ROC' },
      ]},
      { key: 'due_date', label: 'Due date', type: 'date' },
      { key: 'actual_date', label: 'Filing date', type: 'date' },
      { key: 'tax_amount', label: 'Tax (₹)', type: 'number', placeholder: '50000' },
    ],
    buildRequest: (_q, p) => ({
      deadline_type: p.deadline_type || 'gstr3b',
      due_date: p.due_date,
      actual_date: p.actual_date,
      tax_amount: parseFloat(p.tax_amount) || 0,
    }),
    formatResponse: (d) => {
      if (d.error) return d.error;
      return `## Penalty Computation\n**Delay: ${d.days_late ?? d.delay_days} days**\n\n| Component | Amount |\n|---|---|\n| Late Fee | ₹${(d.late_fee ?? 0).toLocaleString('en-IN')} |\n| Interest | ₹${(d.interest ?? 0).toLocaleString('en-IN')} |\n| **Total** | **₹${(d.total_exposure ?? d.total_penalty ?? 0).toLocaleString('en-IN')}** |${d.legal_basis || d.penalty_type ? '\n\n**Legal Basis:** ' + (d.penalty_type || d.legal_basis) : ''}${d.tip ? '\n\n> ' + d.tip : ''}`;
    },
  },
  {
    id: 'mapper',
    label: 'Section Map',
    description: 'IPC/CrPC ↔ BNS/BNSS',
    placeholder: 'Enter section number (e.g., 420, 302)...',
    endpoint: '/tools/section-mapper',
    params: [
      { key: 'direction', label: 'Direction', type: 'select', default: 'old_to_new', options: [
        { value: 'old_to_new', label: 'Old → New' },
        { value: 'new_to_old', label: 'New → Old' },
      ]},
    ],
    buildRequest: (query, p) => ({
      section: query.trim(),
      direction: p.direction || 'old_to_new',
    }),
    formatResponse: (d) => {
      if (!d.found) return d.error || 'Section not found in mapping database.';
      return `## ${d.old_section} → ${d.new_section}\n**${d.title}**\n\n| Old | New |\n|---|---|\n| ${d.old_section} (${d.old_act?.split(',')[0] || ''}) | ${d.new_section} (${d.new_act?.split(',')[0] || ''}) |${d.effective_from ? '\n\nEffective from: ' + d.effective_from : ''}${d.note ? '\n\n> ' + d.note : ''}`;
    },
  },
  {
    id: 'notice-reply',
    label: 'Notice Reply',
    description: 'Auto-draft legal replies',
    placeholder: 'Paste the full notice text here...',
    endpoint: '/tools/notice-auto-reply',
    params: [
      { key: 'client_name', label: 'Client', type: 'text', placeholder: 'M/s Sharma Enterprises' },
    ],
    buildRequest: (query, p) => ({
      notice_text: query,
      client_name: p.client_name || '',
      additional_context: '',
    }),
    formatResponse: (d) => {
      if (d.error) return d.error;
      let r = '';
      if (d.notice_type) r += `**Notice Type:** ${d.notice_type}\n`;
      if (d.demand_amount) r += `**Demand:** ₹${d.demand_amount?.toLocaleString('en-IN')}\n`;
      if (d.financial_year) r += `**FY:** ${d.financial_year}\n\n`;
      if (d.validity_check?.challenge_grounds?.length) {
        r += '### Validity Issues\n';
        d.validity_check.challenge_grounds.forEach(g => {
          r += `- **${g.ground}**: ${g.legal_basis}\n`;
        });
        r += '\n';
      }
      if (d.auto_reply) r += '---\n\n' + d.auto_reply;
      return r || 'No reply generated.';
    },
  },
  {
    id: 'notice-check',
    label: 'Notice Check',
    description: 'Validity & jurisdiction',
    placeholder: 'Notes (optional)...',
    endpoint: '/tools/notice-checker',
    params: [
      { key: 'notice_type', label: 'Type', type: 'select', default: '73', options: [
        { value: '73', label: 'GST S.73' },
        { value: '74', label: 'GST S.74' },
        { value: '143(2)', label: 'IT S.143(2)' },
        { value: '148', label: 'IT S.148/148A' },
      ]},
      { key: 'notice_date', label: 'Notice date', type: 'date' },
      { key: 'financial_year', label: 'FY', type: 'text', placeholder: '2022-23' },
    ],
    buildRequest: (_q, p) => ({
      notice_type: p.notice_type || '73',
      notice_date: p.notice_date,
      financial_year: p.financial_year || '',
      assessment_year: '',
      has_din: true,
      is_fraud_alleged: false,
    }),
    formatResponse: (d) => {
      if (d.error) return d.error;
      let r = `## ${d.overall_validity}\n\n`;
      if (d.limitation_check) r += `**Limitation:** ${d.limitation_check}\n\n`;
      if (d.din_check) r += `**DIN:** ${d.din_check}\n\n`;
      if (d.challenge_grounds?.length) {
        r += '### Challenge Grounds\n';
        d.challenge_grounds.forEach(g => {
          r += `- **${g.ground}** [${g.severity}]: ${g.legal_basis}${g.case_law ? ' — *' + g.case_law + '*' : ''}\n`;
        });
      } else {
        r += '> No automatic challenge grounds detected. Notice appears procedurally valid.';
      }
      return r;
    },
  },
];

const SUGGESTED = [
  {
    label: 'GST Show-Cause Notice',
    text: 'My client received a S.74 SCN for ITC mismatch of ₹48L. The demand was issued 3 years after the relevant date. What are our options?',
    preview: 'Analyze validity, limitation period, and challenge grounds for a S.74 SCN',
  },
  {
    label: 'TDS Classification',
    text: 'Classify TDS for: web developer ₹5L, office rent ₹8L to individual, freight ₹12L, CA retainer ₹3L. Compute amounts.',
    preview: 'Multi-payment TDS computation across sections 194J, 194I, 194C',
  },
  {
    label: 'Old vs New Tax Regime',
    text: 'CTC ₹28L. HRA ₹3.6L, 80C ₹1.5L, 80D ₹25K, NPS ₹50K, HBA interest ₹2L. Compare for AY 2026-27.',
    preview: 'Side-by-side tax liability comparison with detailed breakdowns',
  },
  {
    label: 'Bail Strategy under BNS',
    text: 'Client charged under S.318/316 BNS (old S.420/406 IPC). First-time offender. Compare regular vs anticipatory bail.',
    preview: 'Criminal defense strategy with section mapping and bail parameters',
  },
];

const THINKING_STEPS = [
  'Searching statute database...',
  'Retrieving relevant sections...',
  'Analyzing applicable case law...',
  'Verifying citations...',
  'Preparing response...',
];

export default function AssistantPage() {
  const { getToken, user } = useAuth();
  const [query, setQuery] = useState('');
  const [analysisMode, setAnalysisMode] = useState('partner');
  const [activeMode, setActiveMode] = useState('assistant');
  const [toolParams, setToolParams] = useState({});
  const [loading, setLoading] = useState(false);
  const [thinkingStep, setThinkingStep] = useState(0);
  const [conversations, setConversations] = useState([]);
  const [matters, setMatters] = useState([]);
  const [selectedMatter, setSelectedMatter] = useState('');
  const [showMatterDropdown, setShowMatterDropdown] = useState(false);
  const [attachedFile, setAttachedFile] = useState(null);
  const [showModeSelector, setShowModeSelector] = useState(false);
  const modeSelectorRef = useRef(null);
  const responseEndRef = useRef(null);
  const inputRef = useRef(null);
  const stepTimerRef = useRef(null);
  const fileInputRef = useRef(null);
  const textareaRef = useRef(null);
  const matterRef = useRef(null);

  const currentMode = MODES.find(m => m.id === activeMode) || MODES[0];

  useEffect(() => { fetchMatters(); }, []); // eslint-disable-line

  useEffect(() => {
    if (responseEndRef.current) responseEndRef.current.scrollIntoView({ behavior: 'smooth' });
  }, [conversations]);

  useEffect(() => {
    if (loading && currentMode.isChat) {
      let i = 0;
      stepTimerRef.current = setInterval(() => {
        i = (i + 1) % THINKING_STEPS.length;
        setThinkingStep(i);
      }, 2200);
    } else {
      clearInterval(stepTimerRef.current);
      setThinkingStep(0);
    }
    return () => clearInterval(stepTimerRef.current);
  }, [loading, currentMode.isChat]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + 'px';
    }
  }, [query]);

  useEffect(() => {
    const handleClick = (e) => {
      if (matterRef.current && !matterRef.current.contains(e.target)) setShowMatterDropdown(false);
      if (modeSelectorRef.current && !modeSelectorRef.current.contains(e.target)) setShowModeSelector(false);
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const fetchMatters = async () => {
    try {
      let token = 'dev_mock_token_7128';
      try { token = await getToken() || token; } catch { /* dev fallback */ }
      const res = await fetch(`${API}/matters`, { headers: { 'Authorization': `Bearer ${token}` }, credentials: 'include' });
      if (res.ok) setMatters(await res.json());
    } catch { /* ignore */ }
  };

  const updateParam = (key, value) => {
    setToolParams(prev => ({ ...prev, [key]: value }));
  };

  /* ── Submit dispatcher ── */
  const handleSubmit = async (e, forcedQuery = null) => {
    e?.preventDefault();
    const queryText = (forcedQuery || query).trim();
    if (!queryText && currentMode.isChat) return;
    if (loading) return;

    setQuery('');
    setAttachedFile(null);
    setLoading(true);

    const tempId = Date.now().toString();
    const displayQuery = currentMode.isChat
      ? queryText
      : `[${currentMode.label}] ${queryText || '(structured input)'}`;

    setConversations(prev => [...prev,
      { id: `q_${tempId}`, type: 'query', text: displayQuery, timestamp: new Date() },
      { id: `r_${tempId}`, type: 'response', data: { response_text: '' }, isStreaming: true, timestamp: new Date() },
    ]);

    if (currentMode.isChat) {
      await handleChatSubmit(queryText, tempId);
    } else {
      await handleToolSubmit(queryText, tempId);
    }

    setLoading(false);
  };

  /* ── SSE streaming chat ── */
  const handleChatSubmit = async (queryText, tempId) => {
    try {
      let token = 'dev_mock_token_7128';
      try { token = await getToken() || token; } catch { /* dev fallback */ }

      const res = await fetch(`${API}/assistant/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        credentials: 'include',
        body: JSON.stringify({ query: queryText, mode: analysisMode, matter_id: selectedMatter }),
      });

      if (!res.ok) {
        const errText = await res.text().catch(() => 'Unknown error');
        throw new Error(`Server error ${res.status}: ${errText}`);
      }

      const contentType = res.headers.get('content-type');
      if (contentType && contentType.includes('text/event-stream')) {
        const reader = res.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let done = false;
        let buffer = '';
        let currentResponse = '';
        let currentModels = [];
        let currentSections = [];
        let warRoomStatus = '';
        let partnerPayload = '';

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
                  if (parsed.type === 'fast_chunk') currentResponse += parsed.content;
                  else if (parsed.type === 'fast_complete') { currentModels = parsed.models_used; currentSections = parsed.sections; }
                  else if (parsed.type === 'war_room_status') warRoomStatus = parsed.status;
                  else if (parsed.type === 'partner_payload') partnerPayload += parsed.content;

                  let fullText = currentResponse;
                  if (partnerPayload) fullText += `\n\n---\n\n${partnerPayload}`;

                  setConversations(prev => prev.map(msg =>
                    msg.id === `r_${tempId}`
                      ? { ...msg, data: { response_text: fullText, models_used: currentModels, sections: currentSections, internal_strategy: warRoomStatus && !done ? warRoomStatus : null } }
                      : msg
                  ));
                } catch { /* skip bad chunk */ }
              }
            }
          }
        }
        setConversations(prev => prev.map(msg =>
          msg.id === `r_${tempId}` ? { ...msg, isStreaming: false } : msg
        ));
      } else {
        const data = await res.json();
        setConversations(prev => prev.map(msg =>
          msg.id === `r_${tempId}` ? { ...msg, data, isStreaming: false } : msg
        ));
      }
    } catch (err) {
      setConversations(prev => prev.map(msg =>
        msg.id === `r_${tempId}` ? { ...msg, type: 'error', text: err.message, isStreaming: false } : msg
      ));
    }
  };

  /* ── Tool API call ── */
  const handleToolSubmit = async (queryText, tempId) => {
    try {
      const reqBody = currentMode.buildRequest(queryText, toolParams);
      const res = await api.post(currentMode.endpoint, reqBody);
      const formatted = currentMode.formatResponse(res.data);
      setConversations(prev => prev.map(msg =>
        msg.id === `r_${tempId}` ? { ...msg, data: { response_text: formatted }, isStreaming: false } : msg
      ));
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || 'Tool request failed';
      setConversations(prev => prev.map(msg =>
        msg.id === `r_${tempId}` ? { ...msg, type: 'error', text: errorMsg, isStreaming: false } : msg
      ));
    }
  };

  /* ── Export ── */
  const handleExport = async (format, responseText, title = 'Associate Response') => {
    try {
      let token = 'dev_mock_token_7128';
      try { token = await getToken() || token; } catch { /* dev fallback */ }
      const endpoint = format === 'xlsx' ? 'export/excel' : format === 'docx' ? 'export/word' : 'export/pdf';
      const res = await fetch(`${API}/${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        credentials: 'include',
        body: JSON.stringify({ content: responseText, title, format }),
      });
      if (!res.ok) throw new Error(`Export failed: ${res.status}`);
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${title.replace(/\s+/g, '_')}.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) { console.error('Export error:', err); }
  };

  const handleCreateMatter = async () => {
    const name = prompt('Matter name:');
    if (!name) return;
    try {
      const token = await getToken();
      const res = await fetch(`${API}/matters`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        credentials: 'include',
        body: JSON.stringify({ name }),
      });
      if (res.ok) {
        const matter = await res.json();
        setMatters(prev => [matter, ...prev]);
        setSelectedMatter(matter.matter_id);
      }
    } catch { /* ignore */ }
    setShowMatterDropdown(false);
  };

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setAttachedFile(file);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleFileSubmit = () => {
    if (!attachedFile) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target.result;
      const truncated = typeof content === 'string' ? content.substring(0, 8000) : '';
      const filePrompt = query.trim()
        ? `${query.trim()}\n\n[Attached: ${attachedFile.name}]\n\n${truncated}`
        : `Analyze this document: "${attachedFile.name}"\n\n${truncated}`;
      handleSubmit(null, filePrompt);
    };
    reader.readAsText(attachedFile);
  };

  const selectMode = (modeId) => {
    setActiveMode(modeId);
    setToolParams({});
    inputRef.current?.focus();
  };

  const matterName = selectedMatter
    ? matters.find(m => m.matter_id === selectedMatter)?.name
    : null;
  const hasConversations = conversations.length > 0;

  /* ── Render param field ── */
  const renderParamField = (param) => {
    const value = toolParams[param.key] ?? param.default ?? '';
    const fieldStyle = {
      padding: '7px 10px', fontSize: 13, border: '1px solid #E5E5E5',
      borderRadius: 8, outline: 'none', background: '#fff',
      fontFamily: "'Inter', sans-serif", color: '#0A0A0A',
    };

    if (param.type === 'select') {
      return (
        <select key={param.key} value={value} onChange={e => updateParam(param.key, e.target.value)}
          style={fieldStyle}>
          {param.options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      );
    }

    return (
      <div key={param.key} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <span style={{ fontSize: 12, color: '#999', whiteSpace: 'nowrap', fontWeight: 500 }}>{param.label}</span>
        <input
          type={param.type === 'date' ? 'date' : param.type}
          value={value}
          onChange={e => updateParam(param.key, e.target.value)}
          placeholder={param.placeholder}
          style={{ ...fieldStyle, width: param.type === 'number' ? 100 : param.type === 'date' ? 'auto' : 160 }}
        />
      </div>
    );
  };

  const getGreeting = () => {
    const h = new Date().getHours();
    const name = user?.name?.split(' ')[0] || '';
    const time = h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
    return name ? `${time}, ${name}.` : `${time}.`;
  };

  const nav = useNavigate();

  const selectModeAndClose = (modeId) => {
    selectMode(modeId);
    setShowModeSelector(false);
  };

  /* ═══════════════════ RENDER ═══════════════════ */
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: '#fff', fontFamily: "'Inter', sans-serif" }}>

      {/* ── Top bar ── */}
      <div style={{ height: 52, display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 24px', flexShrink: 0 }}>
        <div ref={matterRef} style={{ position: 'relative' }}>
          <button onClick={() => setShowMatterDropdown(!showMatterDropdown)} style={{
            display: 'flex', alignItems: 'center', gap: 6, padding: '6px 10px', background: 'none', border: 'none',
            borderRadius: 8, fontSize: 14, fontWeight: 500, cursor: 'pointer', color: matterName ? '#0A0A0A' : '#AAA',
          }}>
            <FileText style={{ width: 14, height: 14, opacity: 0.35 }} />
            {matterName || 'New thread'}
            <ChevronDown style={{ width: 10, height: 10, opacity: 0.25 }} />
          </button>
          {showMatterDropdown && (
            <div style={{ position: 'absolute', top: '110%', left: 0, width: 240, background: '#fff', border: '1px solid rgba(0,0,0,0.08)', borderRadius: 10, boxShadow: '0 8px 40px rgba(0,0,0,0.12)', zIndex: 50, padding: 4, animation: 'slideUp 0.2s cubic-bezier(0.16, 1, 0.3, 1)' }}>
              <button onClick={() => { setSelectedMatter(''); setShowMatterDropdown(false); }}
                style={{ width: '100%', textAlign: 'left', padding: '8px 12px', fontSize: 14, color: '#666', background: 'none', border: 'none', cursor: 'pointer', borderRadius: 6 }}
                onMouseEnter={e => e.currentTarget.style.background = '#F5F5F5'} onMouseLeave={e => e.currentTarget.style.background = 'none'}>New thread</button>
              {matters.map(m => (
                <button key={m.matter_id} onClick={() => { setSelectedMatter(m.matter_id); setShowMatterDropdown(false); }}
                  style={{ width: '100%', textAlign: 'left', padding: '8px 12px', fontSize: 14, color: '#0A0A0A', background: 'none', border: 'none', cursor: 'pointer', borderRadius: 6, fontWeight: 500 }}
                  onMouseEnter={e => e.currentTarget.style.background = '#F5F5F5'} onMouseLeave={e => e.currentTarget.style.background = 'none'}>{m.name}</button>
              ))}
              <div style={{ height: 1, background: '#F0F0F0', margin: '4px 8px' }} />
              <button onClick={handleCreateMatter}
                style={{ width: '100%', textAlign: 'left', padding: '8px 12px', fontSize: 14, color: '#0A0A0A', fontWeight: 600, background: 'none', border: 'none', cursor: 'pointer', borderRadius: 6, display: 'flex', alignItems: 'center', gap: 6 }}
                onMouseEnter={e => e.currentTarget.style.background = '#F5F5F5'} onMouseLeave={e => e.currentTarget.style.background = 'none'}>
                <Plus style={{ width: 13, height: 13 }} /> Create matter</button>
            </div>
          )}
        </div>
        <button onClick={() => setAnalysisMode(analysisMode === 'partner' ? 'everyday' : 'partner')}
          style={{ fontSize: 13, fontWeight: 500, padding: '6px 16px', borderRadius: 8, cursor: 'pointer', background: analysisMode === 'partner' ? '#0A0A0A' : '#F5F5F5', color: analysisMode === 'partner' ? '#fff' : '#888', border: 'none', transition: 'all 0.2s' }}>
          {analysisMode === 'partner' ? 'Deep' : 'Quick'}
        </button>
      </div>

      {/* ── Content ── */}
      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', justifyContent: hasConversations ? 'flex-start' : 'center' }}>

        {/* ═══ EMPTY STATE ═══ */}
        {!hasConversations && (
          <div style={{ maxWidth: 680, margin: '0 auto', padding: '0 28px', width: '100%' }}>
            <div style={{ animation: 'fadeIn 0.5s ease-out', textAlign: 'center', marginBottom: 44 }}>
              <h1 style={{ fontFamily: display, fontSize: 42, fontWeight: 600, color: '#0A0A0A', letterSpacing: '-0.04em', lineHeight: 1.1, marginBottom: 8 }}>
                {getGreeting()}
              </h1>
              <p style={{ fontSize: 16, color: '#B0B0B0', lineHeight: 1.5 }}>
                Tax, legal, compliance — grounded and cited.
              </p>
            </div>

            {/* 6 Tool cards — 3x2 grid */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginBottom: 36 }}>
              {MODES.map((mode, i) => (
                <button key={mode.id} onClick={() => { selectModeAndClose(mode.id); inputRef.current?.focus(); }}
                  style={{
                    textAlign: 'left', padding: '18px 20px',
                    border: '1px solid #EBEBEB', borderRadius: 12, background: '#fff', cursor: 'pointer',
                    transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
                    animation: `slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) ${i * 40}ms both`,
                  }}
                  onMouseEnter={e => { e.currentTarget.style.borderColor = '#D0D0D0'; e.currentTarget.style.background = '#FAFAFA'; }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor = '#EBEBEB'; e.currentTarget.style.background = '#fff'; }}>
                  <div style={{ fontSize: 14, fontWeight: 600, color: '#0A0A0A', letterSpacing: '-0.01em', marginBottom: 4 }}>{mode.label}</div>
                  <div style={{ fontSize: 12.5, color: '#B0B0B0', lineHeight: 1.35 }}>{mode.description}</div>
                </button>
              ))}
            </div>

            {/* 4 Suggestions */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 32 }}>
              {SUGGESTED.map((s, i) => (
                <button key={i} onClick={() => { setQuery(s.text); inputRef.current?.focus(); }}
                  style={{
                    textAlign: 'left', padding: '18px 20px', border: '1px solid #EBEBEB', borderRadius: 12, background: '#fff', cursor: 'pointer',
                    transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
                    animation: `slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) ${240 + i * 40}ms both`,
                  }}
                  onMouseEnter={e => { e.currentTarget.style.borderColor = '#D0D0D0'; e.currentTarget.style.background = '#FAFAFA'; }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor = '#EBEBEB'; e.currentTarget.style.background = '#fff'; }}>
                  <div style={{ fontSize: 14.5, fontWeight: 600, color: '#0A0A0A', marginBottom: 5 }}>{s.label}</div>
                  <div style={{ fontSize: 13, color: '#AAA', lineHeight: 1.45 }}>{s.preview}</div>
                </button>
              ))}
            </div>

            <div style={{ textAlign: 'center', animation: 'fadeIn 0.6s ease-out 400ms both' }}>
              <button onClick={() => nav('/app/workflows')}
                style={{ fontSize: 13, fontWeight: 500, color: '#999', background: 'none', border: 'none', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 4, transition: 'color 0.15s' }}
                onMouseEnter={e => e.currentTarget.style.color = '#0A0A0A'} onMouseLeave={e => e.currentTarget.style.color = '#999'}>
                Browse 38 workflows <ArrowRight style={{ width: 12, height: 12 }} />
              </button>
            </div>
          </div>
        )}

        {/* ═══ CONVERSATION ═══ */}
        {hasConversations && (
          <div style={{ padding: '24px 32px 0' }}>
            <div style={{ maxWidth: 700, margin: '0 auto' }}>
              {conversations.map((conv, i) => {
                if (conv.type === 'query') return (
                  <div key={conv.id} style={{ display: 'flex', justifyContent: 'flex-end', margin: '20px 0', animation: 'slideUp 0.25s cubic-bezier(0.16, 1, 0.3, 1)' }}>
                    <div style={{ background: '#F5F5F5', borderRadius: '18px 18px 4px 18px', padding: '12px 16px', maxWidth: '75%' }}>
                      <p style={{ fontSize: 15, color: '#0A0A0A', margin: 0, lineHeight: 1.55, whiteSpace: 'pre-wrap' }}>{conv.text}</p>
                    </div>
                  </div>
                );
                if (conv.type === 'response') return (
                  <div key={conv.id} style={{ margin: '12px 0 28px', animation: 'slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                      <div style={{ width: 24, height: 24, borderRadius: 7, background: '#0A0A0A', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <Scale style={{ width: 11, height: 11, color: '#fff' }} />
                      </div>
                      <span style={{ fontFamily: display, fontSize: 14, fontWeight: 700, color: '#0A0A0A', letterSpacing: '-0.02em' }}>Associate</span>
                    </div>
                    <ResponseCard responseText={conv.data.response_text} sections={conv.data.sections} sources={conv.data.sources} modelUsed={conv.data.model_used} citationsCount={conv.data.citations_count} internalStrategy={conv.data.internal_strategy}
                      onExport={(format) => handleExport(format, conv.data.response_text)}
                      onDraft={() => { setQuery(`Draft a formal document based on: ${conversations[i - 1]?.text || 'the previous analysis'}`); inputRef.current?.focus(); }}
                      onSmartAction={(prompt) => handleSubmit(null, prompt)} />
                  </div>
                );
                if (conv.type === 'error') return (
                  <div key={conv.id} style={{ background: '#FAFAFA', border: '1px solid #EBEBEB', borderRadius: 10, padding: '16px 18px', margin: '16px 0', animation: 'slideUp 0.25s cubic-bezier(0.16, 1, 0.3, 1)' }}>
                    <p style={{ fontSize: 14, color: '#888', margin: '0 0 10px', lineHeight: 1.5 }}>{conv.text}</p>
                    <button onClick={() => setConversations(prev => prev.filter(c => c.id !== conv.id && c.id !== conv.id.replace('r_', 'q_')))}
                      style={{ fontSize: 13, fontWeight: 500, color: '#666', background: '#EBEBEB', border: 'none', borderRadius: 6, padding: '6px 14px', cursor: 'pointer' }}>Dismiss</button>
                  </div>
                );
                return null;
              })}

              {loading && currentMode.isChat && (
                <div style={{ margin: '12px 0 28px', animation: 'slideUp 0.25s cubic-bezier(0.16, 1, 0.3, 1)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                    <div style={{ width: 24, height: 24, borderRadius: 7, background: '#0A0A0A', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <Loader2 style={{ width: 11, height: 11, color: '#fff', animation: 'spin 1s linear infinite' }} />
                    </div>
                    <span style={{ fontFamily: display, fontSize: 14, fontWeight: 700, color: '#0A0A0A' }}>Associate</span>
                  </div>
                  <div style={{ paddingLeft: 32 }}>
                    {THINKING_STEPS.slice(0, thinkingStep + 1).map((step, idx) => (
                      <div key={idx} style={{ fontSize: 14.5, marginBottom: 5, color: idx === thinkingStep ? '#666' : '#CCC', transition: 'color 0.3s', display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ width: 5, height: 5, borderRadius: '50%', background: idx < thinkingStep ? '#0A0A0A' : '#DDD', display: 'inline-block', flexShrink: 0 }} />
                        {step}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {loading && !currentMode.isChat && (
                <div style={{ margin: '16px 0', display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Loader2 style={{ width: 15, height: 15, animation: 'spin 1s linear infinite' }} />
                  <span style={{ fontSize: 14, color: '#999' }}>Processing...</span>
                </div>
              )}
              <div ref={responseEndRef} style={{ height: 16 }} />
            </div>
          </div>
        )}
      </div>

      {/* ═══ INPUT ═══ */}
      <div style={{ padding: '10px 32px 20px', flexShrink: 0 }}>
        <form onSubmit={(e) => { e.preventDefault(); if (attachedFile && currentMode.isChat) handleFileSubmit(); else handleSubmit(e); }}
          style={{ maxWidth: 700, margin: '0 auto' }}>

          {attachedFile && (
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 12px', background: '#F5F5F5', borderRadius: 8, fontSize: 13, color: '#555', marginBottom: 8, fontWeight: 500 }}>
              <Paperclip style={{ width: 13, height: 13 }} /> {attachedFile.name}
              <button type="button" onClick={() => setAttachedFile(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, display: 'flex' }}><X style={{ width: 12, height: 12, color: '#999' }} /></button>
            </div>
          )}

          <div style={{ background: '#F5F5F5', borderRadius: 16, border: '1.5px solid transparent', overflow: 'hidden', transition: 'border-color 0.2s, box-shadow 0.2s, background 0.2s' }}>
            <textarea ref={(el) => { textareaRef.current = el; inputRef.current = el; }}
              value={query} onChange={e => setQuery(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); if (attachedFile && currentMode.isChat) handleFileSubmit(); else handleSubmit(e); } }}
              onFocus={e => { const b = e.target.closest('div'); b.style.borderColor = 'rgba(0,0,0,0.08)'; b.style.boxShadow = '0 0 0 4px rgba(0,0,0,0.02)'; b.style.background = '#F0F0F0'; }}
              onBlur={e => { const b = e.target.closest('div'); b.style.borderColor = 'transparent'; b.style.boxShadow = 'none'; b.style.background = '#F5F5F5'; }}
              placeholder={currentMode.placeholder} rows={1}
              style={{ width: '100%', resize: 'none', background: 'transparent', border: 'none', outline: 'none', padding: '16px 20px 8px', fontSize: 16, color: '#0A0A0A', lineHeight: 1.55, minHeight: 52, maxHeight: 200, boxSizing: 'border-box', fontFamily: "'Inter', sans-serif" }} />

            {/* Bottom: mode dropdown + attach + send */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '4px 12px 10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                {/* Mode selector dropdown */}
                <div ref={modeSelectorRef} style={{ position: 'relative' }}>
                  <button type="button" onClick={() => setShowModeSelector(!showModeSelector)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 5, padding: '6px 12px',
                      background: activeMode !== 'assistant' ? '#0A0A0A' : 'transparent',
                      color: activeMode !== 'assistant' ? '#fff' : '#999',
                      border: activeMode !== 'assistant' ? 'none' : '1px solid #E5E5E5',
                      borderRadius: 8, fontSize: 13, fontWeight: 500, cursor: 'pointer',
                      transition: 'all 0.15s', fontFamily: "'Inter', sans-serif",
                    }}>
                    {currentMode.label}
                    <ChevronDown style={{ width: 11, height: 11, opacity: 0.5 }} />
                  </button>

                  {showModeSelector && (
                    <div style={{
                      position: 'absolute', bottom: '110%', left: 0, width: 220,
                      background: '#fff', border: '1px solid rgba(0,0,0,0.08)', borderRadius: 12,
                      boxShadow: '0 8px 40px rgba(0,0,0,0.12)', zIndex: 50, padding: 4,
                      animation: 'slideUp 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
                    }}>
                      {MODES.map(mode => (
                        <button key={mode.id} type="button" onClick={() => selectModeAndClose(mode.id)}
                          style={{
                            width: '100%', textAlign: 'left', padding: '10px 14px',
                            background: mode.id === activeMode ? '#F5F5F5' : 'none',
                            border: 'none', cursor: 'pointer', borderRadius: 8, transition: 'background 0.1s',
                          }}
                          onMouseEnter={e => { if (mode.id !== activeMode) e.currentTarget.style.background = '#F5F5F5'; }}
                          onMouseLeave={e => { if (mode.id !== activeMode) e.currentTarget.style.background = 'none'; }}>
                          <div style={{ fontSize: 14, fontWeight: 600, color: '#0A0A0A' }}>{mode.label}</div>
                          <div style={{ fontSize: 12, color: '#999', marginTop: 1 }}>{mode.description}</div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                <input ref={fileInputRef} type="file" accept=".pdf,.docx,.doc,.txt,.xlsx,.csv,.json" onChange={handleFileSelect} style={{ display: 'none' }} />
                <button type="button" onClick={() => fileInputRef.current?.click()} title="Attach file"
                  style={{ width: 32, height: 32, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'none', border: 'none', borderRadius: 8, cursor: 'pointer', color: '#CCC', transition: 'color 0.15s' }}
                  onMouseEnter={e => e.currentTarget.style.color = '#888'} onMouseLeave={e => e.currentTarget.style.color = '#CCC'}>
                  <Paperclip style={{ width: 16, height: 16 }} />
                </button>
              </div>

              <button type="submit" disabled={(!query.trim() && !attachedFile) || loading}
                style={{
                  width: 36, height: 36, display: 'flex', alignItems: 'center', justifyContent: 'center',
                  borderRadius: 10, border: 'none',
                  cursor: (query.trim() || attachedFile) && !loading ? 'pointer' : 'default',
                  background: (query.trim() || attachedFile) && !loading ? '#0A0A0A' : '#E0E0E0',
                  color: (query.trim() || attachedFile) && !loading ? '#fff' : '#B0B0B0',
                  transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
                }}
                onMouseEnter={e => { if ((query.trim() || attachedFile) && !loading) { e.currentTarget.style.background = '#1A1A1A'; e.currentTarget.style.transform = 'scale(1.05)'; } }}
                onMouseLeave={e => { e.currentTarget.style.background = (query.trim() || attachedFile) && !loading ? '#0A0A0A' : '#E0E0E0'; e.currentTarget.style.transform = 'scale(1)'; }}>
                {loading ? <Loader2 style={{ width: 15, height: 15, animation: 'spin 1s linear infinite' }} /> : <ArrowUp style={{ width: 17, height: 17 }} />}
              </button>
            </div>
          </div>

          {currentMode.params && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', padding: '10px 4px 0', animation: 'slideUp 0.2s cubic-bezier(0.16, 1, 0.3, 1)' }}>
              {currentMode.params.map(renderParamField)}
            </div>
          )}

          <p style={{ textAlign: 'center', fontSize: 11, color: '#D5D5D5', marginTop: 8 }}>
            Associate verifies citations against statute databases. Always confirm with original sources.
          </p>
        </form>
      </div>
    </div>
  );
}
