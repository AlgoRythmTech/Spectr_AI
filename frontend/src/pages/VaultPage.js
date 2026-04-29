import React, { useState } from 'react';
import {
  FolderOpen, Upload, FileText, X, Briefcase, Clock, Search,
  AlertTriangle, Loader2, ArrowLeft, Download, Copy, Check
} from 'lucide-react';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';
import ResponseCard from '../components/ResponseCard';

const SKILLS = [
  {
    id: 'summarize',
    icon: FileText,
    title: 'Executive Summary',
    desc: 'Partner-ready summary of the entire document — even 1000+ pages. Key numbers, parties, material clauses, deadlines, risks, bottom line.',
    color: '#0A0A0A',
    bg: '#F7F7F8',
    border: 'rgba(0,0,0,0.06)',
  },
  {
    id: 'night_before',
    icon: Briefcase,
    title: 'Night Before Digest',
    desc: 'BLUF summary, fatal errors, precedent matrix, oral argument script, and anticipated bench questions.',
    color: '#0A0A0A',
    bg: '#F7F7F8',
    border: 'rgba(0,0,0,0.06)',
  },
  {
    id: 'timeline',
    icon: Clock,
    title: 'Chronological Timeline',
    desc: 'Extract every date across all documents and build a master sequential timeline of events.',
    color: '#0A0A0A',
    bg: '#F5F5F5',
    border: 'rgba(0,0,0,0.06)',
  },
  {
    id: 'contradictions',
    icon: Search,
    title: 'Cross-Examination Matrix',
    desc: 'Hunt for discrepancies, conflicting dates, inconsistent amounts, and opposing counsel contradictions.',
    color: '#0A0A0A',
    bg: '#FAFAFA',
    border: 'rgba(0,0,0,0.06)',
  },
];

export default function VaultPage() {
  const { getToken } = useAuth();
  const [files, setFiles] = useState([]);
  const [analysisState, setAnalysisState] = useState('idle');
  const [streamedText, setStreamedText] = useState('');
  const [statusMessage, setStatusMessage] = useState('');
  const [activeSkill, setActiveSkill] = useState(null);
  const [copied, setCopied] = useState(false);
  const [customQuery, setCustomQuery] = useState('');

  // Helper: get auth token (falls back to dev token so auth middleware accepts it)
  const authToken = async () => {
    let token = '';

    try { token = await getToken() || token; } catch { /**/ }
    try { token = (await getToken()) || token; } catch { /**/ }
    return token;
  };

  const handleFileUpload = async (e) => {
    const uploadedFiles = Array.from(e.target.files);
    const token = await authToken();
    for (const file of uploadedFiles) {
      let uploaded = false;
      try {
        // Upload to backend vault. CRITICAL: do NOT set Content-Type manually —
        // for multipart the browser must set it with the boundary. Using the
        // native fetch API here because axios v1 inherits its default
        // `Content-Type: application/json` onto FormData requests, which breaks
        // server-side multipart parsing (was causing silent 422s in demo).
        const formData = new FormData();
        formData.append('file', file);
        const baseURL = (api.defaults.baseURL || '/api').replace('://localhost', '://127.0.0.1');
        const res = await fetch(`${baseURL}/vault/upload`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` }, // NO Content-Type — browser sets it
          credentials: 'include',
          body: formData,
        });
        if (!res.ok) {
          const errText = await res.text().catch(() => '');
          console.error('[Vault] upload failed', res.status, errText.slice(0, 300));
          throw new Error(`Upload ${res.status}: ${errText.slice(0, 200)}`);
        }
        const doc = await res.json();
        console.log('[Vault] upload ok', doc);
        setFiles(prev => [...prev, {
          id: doc.document_id || doc.doc_id || Math.random().toString(36).substr(2, 9),
          name: file.name,
          size: (file.size / 1024).toFixed(1) + ' KB',
          doc_id: doc.document_id || doc.doc_id,
        }]);
        uploaded = true;
      } catch (err) {
        console.error('[Vault] upload threw', err);
      }
      if (!uploaded) {
        // Fallback: read file client-side so the user can still analyse it inline.
        // IMPORTANT: only fall back for plain-text formats. For PDF/DOCX the
        // "text" read is raw binary bytes — if we sent that as a query the
        // assistant would echo back `%PDF-1.4 /Type /Catalog …`, which is
        // exactly the bug we hit on 22-Apr-2026.
        const lower = (file.name || '').toLowerCase();
        const isBinary = /\.(pdf|docx|doc|xlsx|xls|pptx|ppt)$/i.test(lower);
        if (isBinary) {
          alert(
            `Upload to the Vault failed for "${file.name}" — usually this means your session expired.\n\n` +
            `Please: open DevTools (F12) → Application → Clear site data → sign in again, then retry.\n\n` +
            `(PDF/DOCX cannot be analysed without a server-side upload; we will not send raw binary as a query.)`
          );
        } else {
          try {
            const text = await file.text();
            setFiles(prev => [...prev, {
              id: Math.random().toString(36).substr(2, 9),
              name: file.name,
              size: (file.size / 1024).toFixed(1) + ' KB',
              content: (text || '').substring(0, 50000),
            }]);
          } catch (readErr) {
            console.error('[Vault] client-side read failed', readErr);
            alert(`Could not upload "${file.name}". Check your connection and retry.`);
          }
        }
      }
    }
  };

  const removeFile = (id) => setFiles(files.filter(f => f.id !== id));

  const triggerSkill = async (skillType, customPromptOverride = '') => {
    if (files.length === 0) {
      alert("Please upload documents to the Vault first.");
      return;
    }

    setActiveSkill(skillType);
    setAnalysisState('analyzing');
    setStreamedText('');
    setStatusMessage(skillType === 'custom_query'
      ? 'Searching across documents…'
      : skillType === 'summarize'
        ? 'Summarising document — this may take 1-2 minutes for large files…'
        : 'Initializing deep analysis...');

    try {
      const token = await authToken();
      // Use backend document IDs if available, otherwise use client-side content
      const hasDocIds = files.some(f => f.doc_id);
      let response;

      if (hasDocIds) {
        // Use proper vault analyze endpoint with document_id (map-reduce pipeline)
        const docId = files.find(f => f.doc_id)?.doc_id;
        const promptForBackend = customPromptOverride
          || (files.length > 1 ? `Analyze all ${files.length} documents together.` : '');
        response = await fetch(`${(api.defaults.baseURL || '/api').replace('://localhost', '://127.0.0.1')}/vault/analyze`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          credentials: 'include',
          body: JSON.stringify({
            document_id: docId,
            analysis_type: skillType,
            custom_prompt: promptForBackend,
          })
        });
      } else {
        // Fallback: send content directly via the assistant query endpoint
        const combinedContent = files.map(f => `--- ${f.name} ---\n${f.content || ''}`).join('\n\n');
        const skillPrompts = {
          summarize: `Produce a partner-ready executive summary of these documents. Include: TL;DR, key numbers, parties & roles, material clauses, deadlines, risks, bottom-line recommendation.\n\n${combinedContent}`,
          night_before: `Perform a "Night Before Hearing" digest on these documents. Give me: BLUF (Bottom Line Up Front), fatal errors in opponent's case, precedent matrix, 3-minute oral argument script, and anticipated bench questions.\n\n${combinedContent}`,
          timeline: `Extract a complete chronological timeline from these documents. Include every date, event, filing, and deadline mentioned.\n\n${combinedContent}`,
          contradictions: `Hunt for contradictions, discrepancies, conflicting dates, inconsistent amounts, and any inconsistencies across these documents.\n\n${combinedContent}`,
          custom_query: `${customPromptOverride || 'Analyze these documents.'}\n\nDocuments:\n${combinedContent}`,
        };
        response = await fetch(`${(api.defaults.baseURL || '/api').replace('://localhost', '://127.0.0.1')}/assistant/query`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          credentials: 'include',
          body: JSON.stringify({
            query: skillPrompts[skillType] || `Analyze: ${combinedContent}`,
            mode: 'partner',
          })
        });
      }

      if (!response.ok) throw new Error("Vault API Error");

      const contentType = response.headers.get('content-type') || '';

      if (contentType.includes('text/event-stream') || contentType.includes('application/x-ndjson')) {
        // Handle streaming response (SSE or NDJSON)
        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let fullText = "";

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;

          const chunks = decoder.decode(value).split('\n');
          for (const chunk of chunks) {
            if (!chunk) continue;
            const line = chunk.startsWith('data: ') ? chunk.substring(6) : chunk;
            if (line === '[DONE]') break;
            try {
              const parsed = JSON.parse(line);
              if (parsed.type === 'vault_status' || parsed.type === 'war_room_status') setStatusMessage(parsed.status);
              else if (parsed.type === 'vault_chunk' || parsed.type === 'fast_chunk') {
                fullText += parsed.content;
                setStreamedText(fullText);
              } else if (parsed.type === 'partner_payload') {
                fullText += '\n\n---\n**Deep Analysis**\n\n' + parsed.content;
                setStreamedText(fullText);
              } else if (parsed.type === 'vault_complete' || parsed.type === 'fast_complete') {
                setAnalysisState('done');
              }
            } catch (e) { /* boundary chunk */ }
          }
        }
      } else {
        // Handle JSON response (non-streaming from vault/analyze or assistant/query)
        const data = await response.json();
        const text = data.response_text || data.analysis || data.result ||
          (data.sections && data.sections[0]?.content) || JSON.stringify(data, null, 2);
        setStreamedText(text);
      }

      setAnalysisState('done');
    } catch (e) {
      console.error(e);
      setAnalysisState('done');
      setStreamedText(`Error: Could not complete analysis. ${e.message}`);
    }
  };

  const copyOutput = () => {
    navigator.clipboard.writeText(streamedText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const renderMarkdown = (text) => {
    if (!text) return null;
    const lines = text.split('\n');
    // Render **bold** as a React element instead of raw HTML injection —
    // eliminates the XSS attack surface from uploaded document text. Any
    // untrusted text that ends up in the analysis response is now rendered
    // as plain text with <strong> inserted only for markdown-bold runs.
    const renderBoldSegments = (text) => {
      const parts = String(text).split(/(\*\*[^*]+\*\*)/g);
      return parts.map((part, idx) => {
        if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
          return <strong key={idx}>{part.slice(2, -2)}</strong>;
        }
        return part;
      });
    };
    return lines.map((line, i) => {
      if (line.startsWith('## ')) return <h2 key={i} style={{ fontSize: 18, fontWeight: 700, color: '#0A0A0A', margin: '20px 0 8px' }}>{line.replace('## ', '')}</h2>;
      if (line.startsWith('### ')) return <h3 key={i} style={{ fontSize: 15, fontWeight: 700, color: '#374151', margin: '16px 0 6px' }}>{line.replace('### ', '')}</h3>;
      if (line.startsWith('> ')) return <blockquote key={i} style={{ borderLeft: '3px solid #0A0A0A', paddingLeft: 14, margin: '8px 0', color: '#4B5563', fontSize: 13, fontStyle: 'italic' }}>{line.replace('> ', '')}</blockquote>;
      if (line.startsWith('- ')) return <li key={i} style={{ fontSize: 13, color: '#374151', lineHeight: 1.7, marginLeft: 16 }}>{line.replace('- ', '')}</li>;
      if (line.trim() === '') return <div key={i} style={{ height: 8 }} />;
      return <p key={i} style={{ fontSize: 13.5, color: '#374151', lineHeight: 1.75, margin: '4px 0' }}>{renderBoldSegments(line)}</p>;
    });
  };

  return (
    <div style={{ display: 'flex', height: '100%', background: 'linear-gradient(160deg, #FAFAFA 0%, #F3F3F4 40%, #F0F0F1 100%)' }} data-testid="vault-page">
      {/* Sidebar - File Panel */}
      <div style={{ width: 280, borderRight: '1px solid rgba(0,0,0,0.06)', display: 'flex', flexDirection: 'column', flexShrink: 0, background: 'rgba(255,255,255,0.7)', backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)' }}>
        <div style={{ padding: '16px 16px 12px', borderBottom: '1px solid rgba(0,0,0,0.06)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <FolderOpen style={{ width: 16, height: 16, color: '#0A0A0A' }} />
            <span style={{ fontSize: 14, fontWeight: 700, color: '#0A0A0A' }}>Document Vault</span>
          </div>
          <label style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
            padding: '10px 14px', borderRadius: 100, cursor: 'pointer',
            background: '#0A0A0A', color: '#fff', fontSize: 12, fontWeight: 600,
          }}>
            <input type="file" multiple onChange={handleFileUpload} style={{ display: 'none' }} accept=".pdf,.docx,.txt" />
            <Upload style={{ width: 13, height: 13 }} /> Upload Documents
          </label>
        </div>

        <div style={{ flex: 1, overflow: 'auto', padding: 8 }}>
          {files.length === 0 ? (
            <div style={{ padding: 24, textAlign: 'center', color: '#94A3B8' }}>
              <FileText style={{ width: 28, height: 28, margin: '0 auto 8px', opacity: 0.4 }} />
              <p style={{ fontSize: 12, fontWeight: 500 }}>No documents yet</p>
              <p style={{ fontSize: 11 }}>Upload PDFs, DOCX, or TXT files</p>
            </div>
          ) : (
            files.map(file => (
              <div key={file.id} style={{
                display: 'flex', alignItems: 'center', gap: 8, padding: '8px 10px',
                borderRadius: 12, marginBottom: 2, background: 'rgba(255,255,255,0.6)', border: '1px solid rgba(255,255,255,0.3)',
                backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)', boxShadow: '0 4px 24px rgba(0,0,0,0.04)',
                transition: 'all 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
              }}>
                <FileText style={{ width: 14, height: 14, color: '#6B7280', flexShrink: 0 }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: '#374151', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{file.name}</div>
                  <div style={{ fontSize: 10, color: '#94A3B8' }}>{file.size}</div>
                </div>
                <button onClick={() => removeFile(file.id)} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 2 }}>
                  <X style={{ width: 12, height: 12, color: '#94A3B8' }} />
                </button>
              </div>
            ))
          )}
        </div>

        <div style={{ padding: '8px 12px', borderTop: '1px solid rgba(0,0,0,0.06)', fontSize: 11, color: '#94A3B8', textAlign: 'center' }}>
          {files.length} document{files.length !== 1 ? 's' : ''} loaded
        </div>
      </div>

      {/* Main Panel */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {analysisState === 'idle' && (
          <div style={{ flex: 1, padding: 40, overflow: 'auto' }}>
            <div style={{ maxWidth: 700, margin: '0 auto' }}>
              <h2 style={{ fontSize: 22, fontWeight: 700, color: '#0A0A0A', marginBottom: 6, letterSpacing: '-0.02em' }}>
                {files.length === 0 ? 'Upload documents to begin' : `Analyse ${files.length} document${files.length !== 1 ? 's' : ''}`}
              </h2>
              <p style={{ fontSize: 14, color: '#6B7280', marginBottom: 24, lineHeight: 1.5 }}>
                Ask anything, or pick a forensic workflow below.
              </p>

              {/* ─── Ask Anything input ─── */}
              <div style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '4px 4px 4px 16px',
                background: 'rgba(255,255,255,0.85)',
                border: '1px solid rgba(0,0,0,0.08)',
                borderRadius: 14,
                marginBottom: 28,
                boxShadow: '0 4px 20px rgba(0,0,0,0.04)',
                opacity: files.length === 0 ? 0.5 : 1,
              }}>
                <Search style={{ width: 15, height: 15, color: '#999', flexShrink: 0 }} />
                <input
                  value={customQuery}
                  onChange={e => setCustomQuery(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === 'Enter' && customQuery.trim() && files.length > 0) {
                      triggerSkill('custom_query', customQuery.trim());
                    }
                  }}
                  placeholder="Find anything — 'what's the limitation deadline?', 'summarise Section 7', 'find every mention of ₹2 crore'…"
                  disabled={files.length === 0}
                  style={{
                    flex: 1, border: 'none', outline: 'none', background: 'transparent',
                    fontSize: 14, color: '#0A0A0A', padding: '12px 4px', fontFamily: 'inherit',
                  }}
                />
                <button
                  onClick={() => customQuery.trim() && triggerSkill('custom_query', customQuery.trim())}
                  disabled={!customQuery.trim() || files.length === 0}
                  style={{
                    padding: '8px 16px',
                    background: customQuery.trim() && files.length > 0 ? '#0A0A0A' : 'rgba(0,0,0,0.1)',
                    color: customQuery.trim() && files.length > 0 ? '#fff' : '#999',
                    border: 'none', borderRadius: 10, fontSize: 13, fontWeight: 600,
                    cursor: customQuery.trim() && files.length > 0 ? 'pointer' : 'default',
                    fontFamily: 'inherit', transition: 'all 0.15s',
                  }}
                >
                  Ask
                </button>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {SKILLS.map(skill => (
                  <div key={skill.id} onClick={() => triggerSkill(skill.id)} style={{
                    display: 'flex', gap: 16, padding: 24, borderRadius: 14,
                    background: 'rgba(255,255,255,0.6)', backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)',
                    border: '1px solid rgba(255,255,255,0.3)', boxShadow: '0 4px 24px rgba(0,0,0,0.04)',
                    cursor: files.length > 0 ? 'pointer' : 'not-allowed',
                    opacity: files.length > 0 ? 1 : 0.5,
                    transition: 'all 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
                  }}
                    onMouseEnter={e => { if (files.length > 0) { e.currentTarget.style.background = 'rgba(255,255,255,0.85)'; e.currentTarget.style.boxShadow = '0 8px 32px rgba(0,0,0,0.06)'; e.currentTarget.style.transform = 'translateY(-2px)'; } }}
                    onMouseLeave={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.6)'; e.currentTarget.style.boxShadow = '0 4px 24px rgba(0,0,0,0.04)'; e.currentTarget.style.transform = 'translateY(0)'; }}
                  >
                    <div style={{ width: 44, height: 44, background: skill.bg, borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                      <skill.icon style={{ width: 20, height: 20, color: skill.color }} />
                    </div>
                    <div>
                      <h3 style={{ fontSize: 15, fontWeight: 700, color: '#0A0A0A', marginBottom: 4 }}>{skill.title}</h3>
                      <p style={{ fontSize: 13, color: '#6B7280', lineHeight: 1.5, margin: 0 }}>{skill.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {(analysisState === 'analyzing' || analysisState === 'done') && (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            {/* Toolbar */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 24px', borderBottom: '1px solid rgba(0,0,0,0.06)', flexShrink: 0, background: 'rgba(255,255,255,0.7)', backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                {analysisState === 'done' && (
                  <button onClick={() => { setAnalysisState('idle'); setStreamedText(''); }} style={{
                    display: 'flex', alignItems: 'center', gap: 4, padding: '6px 12px',
                    fontSize: 12, fontWeight: 600, color: '#6B7280', background: 'rgba(255,255,255,0.6)',
                    border: '1px solid rgba(0,0,0,0.06)', borderRadius: 100, cursor: 'pointer',
                    transition: 'all 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
                  }}>
                    <ArrowLeft style={{ width: 12, height: 12 }} /> Back
                  </button>
                )}
                {analysisState === 'analyzing' && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Loader2 style={{ width: 14, height: 14, color: '#0A0A0A', animation: 'spin 1s linear infinite' }} />
                    <span style={{ fontSize: 12, fontWeight: 600, color: '#0A0A0A' }}>{statusMessage}</span>
                  </div>
                )}
                {analysisState === 'done' && activeSkill && (
                  <span style={{ fontSize: 12, fontWeight: 700, color: SKILLS.find(s => s.id === activeSkill)?.color || '#000' }}>
                    {SKILLS.find(s => s.id === activeSkill)?.title || 'Analysis'}
                  </span>
                )}
              </div>
              {analysisState === 'done' && (
                <button onClick={copyOutput} style={{
                  display: 'flex', alignItems: 'center', gap: 4, padding: '6px 12px',
                  fontSize: 11, fontWeight: 600, color: '#6B7280', background: 'rgba(255,255,255,0.6)',
                  border: '1px solid rgba(0,0,0,0.06)', borderRadius: 100, cursor: 'pointer',
                  transition: 'all 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
                }}>
                  {copied ? <Check style={{ width: 11, height: 11, color: '#000' }} /> : <Copy style={{ width: 11, height: 11 }} />}
                  {copied ? 'Copied' : 'Copy Output'}
                </button>
              )}
            </div>

            {/* Output — uses ResponseCard for consistent typography with Chat */}
            <div style={{ flex: 1, overflow: 'auto', padding: '24px 40px' }}>
              <div style={{ maxWidth: 820, margin: '0 auto' }}>
                <ResponseCard
                  responseText={streamedText}
                  sections={[]}
                  sources={[]}
                  citations={[]}
                />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
