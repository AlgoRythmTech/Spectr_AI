import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import ResponseCard from '../components/ResponseCard';
import {
  Send, Plus, ChevronDown, Sparkles, FileText, Loader2,
  Zap, Brain, Scale, BarChart3, FileSearch, ChevronRight, Paperclip, Upload
} from 'lucide-react';

const API = process.env.NODE_ENV === 'development' ? 'http://localhost:8000/api' : '/api';

const SUGGESTED = [
  { icon: Scale, label: 'GST SCN Defense', text: 'Draft a reply to a GST Show Cause Notice under Section 73 for alleged ITC mismatch of ₹48 lakhs in FY 2023-24.' },
  { icon: FileSearch, label: 'Cheque Bounce', text: 'My client received a dishonoured cheque of ₹12 lakhs. Draft a legal notice under Section 138 NI Act with all statutory requirements.' },
  { icon: BarChart3, label: 'TDS Analysis', text: 'Classify these payments under correct TDS sections: Digital marketing ₹4L, AMC of software ₹3L, Freight charges ₹8L, Legal fees ₹2L.' },
  { icon: Brain, label: 'Bail Application', text: 'Draft a bail application for an accused charged under Sections 406 and 420 IPC. The accused is a first-time offender with no flight risk.' },
];

const COUNCIL_STEPS = [
  'Searching verified statute databases...',
  'Retrieving precedent judgments from IndianKanoon...',
  'Cross-referencing GSTIN registrations...',
  'Validating citation integrity...',
  'Analyzing statutory intersections...',
  'Compiling advisory memo...',
];

export default function AssistantPage() {
  const { getToken } = useAuth();
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState('partner');
  const [loading, setLoading] = useState(false);
  const [councilStep, setCouncilStep] = useState(0);
  const [conversations, setConversations] = useState([]);
  const [matters, setMatters] = useState([]);
  const [selectedMatter, setSelectedMatter] = useState('');
  const [showMatterDropdown, setShowMatterDropdown] = useState(false);
  const responseEndRef = useRef(null);
  const inputRef = useRef(null);
  const stepTimerRef = useRef(null);
  const fileInputRef = useRef(null);

  useEffect(() => { fetchMatters(); }, []);

  useEffect(() => {
    if (responseEndRef.current) responseEndRef.current.scrollIntoView({ behavior: 'smooth' });
  }, [conversations]);

  useEffect(() => {
    if (loading) {
      let i = 0;
      stepTimerRef.current = setInterval(() => {
        i = (i + 1) % COUNCIL_STEPS.length;
        setCouncilStep(i);
      }, 1800);
    } else {
      clearInterval(stepTimerRef.current);
      setCouncilStep(0);
    }
    return () => clearInterval(stepTimerRef.current);
  }, [loading]);

  const fetchMatters = async () => {
    try {
      let token = 'dev_mock_token_7128';
      try { token = await getToken() || token; } catch { /* dev fallback */ }
      const res = await fetch(`${API}/matters`, { headers: { 'Authorization': `Bearer ${token}` }, credentials: 'include' });
      if (res.ok) setMatters(await res.json());
    } catch {}
  };

  const handleSubmit = async (e, forcedQuery = null) => {
    e?.preventDefault();
    const queryToSubmit = forcedQuery || query;
    if (!queryToSubmit.trim() || loading) return;
    const userQuery = queryToSubmit.trim();
    setQuery('');
    setLoading(true);
    
    // Create a temporary ID for the new message so we can update it in place
    const tempId = Date.now().toString();
    setConversations(prev => [...prev, { id: `q_${tempId}`, type: 'query', text: userQuery, timestamp: new Date() }]);
    setConversations(prev => [...prev, { id: `r_${tempId}`, type: 'response', data: { response_text: '', models_used: [], sections: [] }, isStreaming: true, timestamp: new Date() }]);

    try {
      let token = 'dev_mock_token_7128';
      try { token = await getToken() || token; } catch { /* use dev token */ }
      
      const res = await fetch(`${API}/assistant/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        credentials: 'include',
        body: JSON.stringify({ query: userQuery, mode, matter_id: selectedMatter }),
      });
      
      if (!res.ok) {
        const errText = await res.text().catch(() => 'Unknown error');
        throw new Error(`Server error ${res.status}: ${errText}`);
      }

      // Check if the response is event-stream
      const contentType = res.headers.get("content-type");
      if (contentType && contentType.includes("text/event-stream")) {
        const reader = res.body.getReader();
        const decoder = new TextDecoder("utf-8");
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
            buffer = payloads.pop() || ''; // Keep incomplete part in buffer
            
            for (const payload of payloads) {
              const lines = payload.split('\n');
              for (const line of lines) {
                if (line.trim() === '') continue;
                if (line.startsWith('data: ')) {
                  const dataStr = line.substring(6);
                  if (dataStr === '[DONE]') {
                    done = true;
                    break;
                  }
                  
                  try {
                    const parsed = JSON.parse(dataStr);
                    if (parsed.type === 'fast_chunk') {
                      currentResponse += parsed.content;
                    } else if (parsed.type === 'fast_complete') {
                      currentModels = parsed.models_used;
                      currentSections = parsed.sections;
                    } else if (parsed.type === 'war_room_status') {
                      warRoomStatus = parsed.status;
                    } else if (parsed.type === 'partner_payload') {
                      partnerPayload += parsed.content;
                    }
                    
                    // Construct the full text by appending war room and partner payloads
                    let fullText = currentResponse;
                    if (partnerPayload) {
                      fullText += `\n\n---\n**Indepth Analysis**\n\n${partnerPayload}`;
                    }
                    
                    // We DO NOT append warRoomStatus to fullText so it doesn't pollute the final output.
                    
                    // Update the specific message
                    setConversations(prev => prev.map(msg => {
                      if (msg.id === `r_${tempId}`) {
                        return { 
                          ...msg, 
                          data: { 
                            response_text: fullText, 
                            models_used: currentModels, 
                            sections: currentSections,
                            internal_strategy: warRoomStatus && !done ? warRoomStatus : null // Only pass it while streaming to display as a thinking block
                          } 
                        };
                      }
                      return msg;
                    }));
                  } catch (e) {
                    console.error('Error parsing SSE chunk:', e, dataStr.substring(0, 50) + "...");
                  }
                }
              }
            }
          }
        }
        
        // Finalize streaming
        setConversations(prev => prev.map(msg => msg.id === `r_${tempId}` ? { ...msg, isStreaming: false } : msg));
        
      } else {
        // Fallback for non-streaming old API
        const data = await res.json();
        setConversations(prev => prev.map(msg => msg.id === `r_${tempId}` ? { ...msg, type: 'response', data, isStreaming: false } : msg));
      }
    } catch (err) {
      setConversations(prev => prev.map(msg => msg.id === `r_${tempId}` ? { ...msg, type: 'error', text: `Error: ${err.message}`, isStreaming: false } : msg));
    } finally { setLoading(false); }
  };

  const handleExport = async (format, responseText, title = 'Associate Response') => {
    try {
      let token = 'dev_mock_token_7128';
      try { token = await getToken() || token; } catch { /* dev fallback */ }
      const endpoint = format === 'docx' ? 'export/word' : format === 'xlsx' ? 'export/excel' : 'export/pdf';
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
      a.download = `${title.replace(/\s+/g, '_')}.${format === 'xlsx' ? 'xlsx' : format === 'docx' ? 'docx' : 'pdf'}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Export error:', err);
      alert(`Export to ${format.toUpperCase()} failed. Is the backend running?`);
    }
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
    } catch {}
    setShowMatterDropdown(false);
  };

  // General Document Upload Handler
  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    // Read the file content client-side
    const reader = new FileReader();
    reader.onload = async (event) => {
      const fileContent = event.target.result;
      
      // Auto-submit a query with the document context
      const documentQuery = `Please analyze the following uploaded document titled "${file.name}":\n\n${typeof fileContent === 'string' ? fileContent.substring(0, 5000) : '...'}`;
      
      // We manually clear the file input
      if (fileInputRef.current) fileInputRef.current.value = '';
      
      // Call handleSubmit directly with the document text to bypass state closure bugs
      handleSubmit(null, documentQuery);
    };
    
    // Read as text for simplicity
    reader.readAsText(file);
  };

  const matterName = selectedMatter ? matters.find(m => m.matter_id === selectedMatter)?.name : null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: '#FFFFFF', fontFamily: 'inherit' }} data-testid="assistant-page">

      {/* Top Bar */}
      <div className="bg-[#FFFFFF] border-b border-[#E5E7EB]" style={{ height: 64, display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 32px', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {/* Matter selector */}
          <div style={{ position: 'relative' }}>
            <button onClick={() => setShowMatterDropdown(!showMatterDropdown)}
              className="flex items-center gap-2 px-3 py-1.5 bg-[#FAFAFA] border border-[#E5E7EB] rounded-[6px] hover:bg-[#F3F4F6] transition-colors"
              style={{
                color: matterName ? '#000000' : '#6B7280', fontSize: 13, fontWeight: 600, cursor: 'pointer', tracking: '-0.01em'
              }}
              data-testid="matter-selector">
              <FileText style={{ width: 14, height: 14 }} />
              {matterName || 'New Strategic Query'}
              <ChevronDown style={{ width: 14, height: 14, opacity: 0.5 }} />
            </button>
            {showMatterDropdown && (
              <div style={{
                position: 'absolute', top: '120%', left: 0, width: 260,
                background: '#FFFFFF', border: '1px solid #E5E7EB', borderRadius: 8, zIndex: 50,
                boxShadow: '0 12px 40px rgba(0,0,0,0.08)', overflow: 'hidden', padding: 4
              }}>
                <button onClick={() => { setSelectedMatter(''); setShowMatterDropdown(false); }}
                  className="w-full text-left px-4 py-2.5 text-[13px] text-[#4B5563] hover:bg-[#F3F4F6] rounded flex items-center gap-2 font-medium transition-colors">
                  <Sparkles style={{ width: 14, height: 14 }} /> New Strategic Query
                </button>
                <div className="h-px bg-[#E5E7EB] my-1 mx-2" />
                {matters.map(m => (
                  <button key={m.matter_id} onClick={() => { setSelectedMatter(m.matter_id); setShowMatterDropdown(false); }}
                    className="w-full text-left px-4 py-2 text-[13px] text-[#000000] hover:bg-[#F3F4F6] rounded font-medium transition-colors">
                    {m.name}
                  </button>
                ))}
                <div className="h-px bg-[#E5E7EB] my-1 mx-2" />
                <button onClick={handleCreateMatter}
                  className="w-full text-left px-4 py-2.5 text-[13px] text-[#000000] font-bold hover:bg-[#F3F4F6] rounded flex items-center gap-2 transition-colors">
                  <Plus style={{ width: 14, height: 14 }} /> Initialize Matter
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Mode toggle */}
        <button onClick={() => setMode(mode === 'partner' ? 'everyday' : 'partner')}
          className={`flex items-center gap-2 px-4 py-1.5 rounded-[20px] text-[13px] font-bold tracking-tight transition-all ${mode === 'partner' ? 'bg-[#000000] text-white' : 'bg-[#FAFAFA] border border-[#E5E7EB] text-[#4B5563] hover:border-[#000000]'}`}
          data-testid="mode-toggle">
          {mode === 'partner' ? <><Zap style={{ width: 12, height: 12 }} /> PROFESSIONAL</> : <><Sparkles style={{ width: 12, height: 12 }} /> ASSOCIATE</>}
        </button>
      </div>

      {/* Conversation area */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '32px 32px 0' }} data-testid="conversation-area">
        {/* Empty state */}
        {conversations.length === 0 && (
          <div style={{ maxWidth: 800, margin: '0 auto', paddingTop: 64, paddingBottom: 64 }}>
            <div className="mb-8">
              <div style={{
                width: 64, height: 64, background: '#FAFAFA', border: '1px solid #E5E7EB', borderRadius: 16,
                display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '24px', boxShadow: '0 2px 10px rgba(0,0,0,0.02)'
              }}>
                <Scale style={{ width: 32, height: 32, color: '#000000' }} />
              </div>
              <h2 className="text-[46px] font-bold text-[#000000] tracking-tightest leading-none mb-4">
                The Infinite Intelligence Engine.
              </h2>
              <p className="text-[17px] text-[#4B5563] leading-relaxed max-w-2xl font-medium">
                Command a multi-agent orchestrated cluster to synthesize statutory law, 
                extract forensic data, cross-reference Indian Kanoon precedents, and formulate elite Big 4 defense strategies instantly.
              </p>
            </div>

            {/* Model badges */}
            <div style={{ display: 'flex', gap: 8, marginBottom: 48, flexWrap: 'wrap' }}>
              {['Ind AS 12 Depth', 'NJDG Precedents', 'MCA21 Database', 'Income Tax / GST Scans'].map((m, i) => (
                <span key={i} style={{
                  fontSize: 12, fontWeight: 700, padding: '4px 12px',
                  background: '#FAFAFA', border: '1px solid #E5E7EB',
                  borderRadius: '4px', color: '#4B5563', tracking: '0.05em', textTransform: 'uppercase'
                }}>{m}</span>
              ))}
            </div>

            {/* Suggested queries */}
            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)', gap: 12 }}>
              {SUGGESTED.map((s, i) => (
                <button key={i} onClick={() => { setQuery(s.text); inputRef.current?.focus(); }}
                  className="text-left p-5 border border-[#E5E7EB] rounded-[12px] hover:border-[#000000] active:bg-[#FAFAFA] transition-all bg-[#FFFFFF] shadow-sm hover:shadow-md flex flex-col gap-3 group">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-full bg-[#FAFAFA] border border-[#F3F4F6] flex items-center justify-center group-hover:bg-[#000000] group-hover:text-white transition-colors">
                      <s.icon style={{ width: 14, height: 14 }} className="text-[#000] group-hover:text-white" />
                    </div>
                    <span className="text-[13px] font-bold text-[#000000] tracking-tight">{s.label}</span>
                  </div>
                  <span className="text-[14px] text-[#4B5563] leading-relaxed">{s.text}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        <div style={{ maxWidth: 860, margin: '0 auto' }}>
          {conversations.map((conv, i) => {
            if (conv.type === 'query') return (
              <div key={i} className="animate-in fade-in slide-in-from-bottom-2 duration-300" style={{ display: 'flex', justifyContent: 'flex-end', margin: '24px 0' }}>
                <div style={{
                  background: '#F3F4F6', borderRadius: '16px 16px 4px 16px',
                  padding: '16px 20px', maxWidth: '75%', border: '1px solid #E5E7EB'
                }}>
                  <p className="text-[15px] text-[#000000] m-0 leading-relaxed font-medium">{conv.text}</p>
                </div>
              </div>
            );
            if (conv.type === 'response') return (
              <div key={i} className="animate-in fade-in slide-in-from-bottom-4 duration-500" style={{ margin: '24px 0 40px' }}>
                <ResponseCard
                  responseText={conv.data.response_text}
                  sections={conv.data.sections}
                  sources={conv.data.sources}
                  modelUsed={conv.data.model_used}
                  citationsCount={conv.data.citations_count}
                  internalStrategy={conv.data.internal_strategy}
                  onExport={(format) => handleExport(format, conv.data.response_text)}
                  onDraft={() => { setQuery(`Draft a formal document based on: ${conversations[i - 1]?.text || 'the previous analysis'}`); inputRef.current?.focus(); }}
                />
              </div>
            );
            if (conv.type === 'error') return (
              <div key={i} style={{
                background: '#FFFFFF', border: '1px solid #EF4444', borderRadius: 8,
                padding: '16px 20px', fontSize: 14, color: '#DC2626', margin: '24px 0', fontWeight: 500
              }}>
                <div className="flex items-center gap-2"><div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" /> {conv.text}</div>
              </div>
            );
            return null;
          })}

          {/* Perplexity-style Thinking Indicator — disappears when response arrives */}
          {loading && (
            <div className="animate-in fade-in slide-in-from-bottom-2 duration-300" style={{ margin: '24px 0 40px', maxWidth: 860, marginLeft: 'auto', marginRight: 'auto' }}>
              <div style={{
                background: '#FFFFFF', border: '1px solid #E5E7EB', borderRadius: 12,
                padding: '16px 20px', boxShadow: '0 2px 8px rgba(0,0,0,0.03)',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
                  <div style={{
                    width: 20, height: 20, borderRadius: '50%',
                    border: '2px solid #E5E7EB', borderTopColor: '#000',
                    animation: 'spin 0.8s linear infinite',
                  }} />
                  <span style={{ fontSize: 14, fontWeight: 600, color: '#111827', letterSpacing: '-0.01em' }}>Reasoning...</span>
                </div>
                
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6, paddingLeft: 30 }}>
                  {COUNCIL_STEPS.slice(0, councilStep + 1).map((step, idx) => (
                    <div key={idx} style={{
                      display: 'flex', alignItems: 'center', gap: 8,
                      fontSize: 13, color: idx === councilStep ? '#374151' : '#9CA3AF',
                      fontWeight: idx === councilStep ? 500 : 400,
                      transition: 'all 0.3s ease',
                    }}>
                      {idx < councilStep 
                        ? <span style={{ color: '#10B981', fontSize: 14 }}>✓</span>
                        : <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#000', animation: 'pulse 1.5s infinite' }} />
                      }
                      {step}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
          <div ref={responseEndRef} style={{ height: 20 }} />
        </div>
      </div>

      {/* Premium Input Box */}
      <div style={{
        padding: '20px 32px 32px',
        background: 'linear-gradient(0deg, #FFFFFF 85%, rgba(255,255,255,0) 100%)',
        flexShrink: 0,
      }}>
        <form onSubmit={handleSubmit} style={{ maxWidth: 860, margin: '0 auto', position: 'relative' }}>
          <div style={{ 
            background: '#FFFFFF', border: '1px solid #D1D5DB', borderRadius: 16,
            boxShadow: '0 8px 30px rgba(0,0,0,0.06)', overflow: 'hidden', transition: 'border-color 0.2s',
          }} className="focus-within:border-[#000000] focus-within:ring-1 focus-within:ring-[#000]">
            <textarea
              ref={inputRef}
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit(e); } }}
              placeholder="Deploy the Associate. Draft SCN Replies, extract ITC data, analyze precedent rulings..."
              rows={1}
              style={{
                width: '100%', resize: 'none', background: 'transparent',
                border: 'none', outline: 'none', padding: '20px 24px',
                fontSize: 15, color: '#000000', lineHeight: 1.6,
                minHeight: 64, maxHeight: 240, boxSizing: 'border-box',
                fontFamily: 'inherit',
              }}
              className="placeholder:text-[#9CA3AF]"
              data-testid="query-input"
            />
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '12px 20px', borderTop: '1px solid #F3F4F6', background: '#FAFAFA'
            }}>
              <span style={{ fontSize: 11, color: '#9CA3AF', fontFamily: 'monospace', tracking: 'tight' }}>
                <kbd className="font-sans px-1 py-0.5 border border-[#E5E7EB] rounded bg-[#FFF] text-[#6B7280]">Enter</kbd> to deploy · <kbd className="font-sans px-1 py-0.5 border border-[#E5E7EB] rounded bg-[#FFF] text-[#6B7280]">Shift+Enter</kbd> for newline
              </span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {/* Attach file */}
                <input 
                  ref={fileInputRef}
                  type="file" 
                  accept=".pdf,.docx,.doc,.txt,.xlsx,.csv" 
                  onChange={handleFileUpload}
                  style={{ display: 'none' }} 
                  id="document-upload"
                />
                <button 
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  title="Upload document for analysis"
                  className="flex items-center gap-1.5 px-3 py-2 rounded-[6px] text-[12px] font-semibold text-[#6B7280] hover:text-[#000] hover:bg-[#F3F4F6] transition-all border border-transparent hover:border-[#E5E7EB]"
                >
                  <Paperclip style={{ width: 13, height: 13 }} />
                </button>
              <button type="submit" disabled={!query.trim() || loading}
                className={`flex items-center gap-2 px-5 py-2.5 rounded-[8px] text-[13px] font-bold tracking-tight transition-all ${
                  query.trim() && !loading ? 'bg-[#000000] text-white shadow-md hover:bg-[#111]' : 'bg-[#F3F4F6] text-[#9CA3AF] cursor-not-allowed'
                }`}
                data-testid="submit-query-btn">
                {loading ? <Loader2 style={{ width: 14, height: 14, animation: 'spin 1s linear infinite' }} /> : <Send style={{ width: 14, height: 14 }} />}
                EXECUTE
              </button>
              </div>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
