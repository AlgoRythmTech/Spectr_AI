import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import ResponseCard from '../components/ResponseCard';
import {
  Send, Mic, Plus, ChevronDown, Sparkles, ToggleLeft, ToggleRight,
  Clock, Scale, FileText, Loader2
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function AssistantPage() {
  const { user } = useAuth();
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState('partner');
  const [loading, setLoading] = useState(false);
  const [conversations, setConversations] = useState([]);
  const [matters, setMatters] = useState([]);
  const [selectedMatter, setSelectedMatter] = useState('');
  const [showMatterDropdown, setShowMatterDropdown] = useState(false);
  const responseEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    fetchMatters();
  }, []);

  useEffect(() => {
    if (responseEndRef.current) {
      responseEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [conversations]);

  const fetchMatters = async () => {
    try {
      const res = await fetch(`${API}/matters`, { credentials: 'include' });
      if (res.ok) setMatters(await res.json());
    } catch {}
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim() || loading) return;

    const userQuery = query.trim();
    setQuery('');
    setLoading(true);

    setConversations(prev => [...prev, { type: 'query', text: userQuery, timestamp: new Date() }]);

    try {
      const res = await fetch(`${API}/assistant/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          query: userQuery,
          mode,
          matter_id: selectedMatter,
        }),
      });

      if (!res.ok) throw new Error('Query failed');
      const data = await res.json();

      setConversations(prev => [...prev, {
        type: 'response',
        data,
        timestamp: new Date(),
      }]);
    } catch (err) {
      setConversations(prev => [...prev, {
        type: 'error',
        text: 'Failed to process query. Please try again.',
        timestamp: new Date(),
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (format, responseText, title = 'Associate Response') => {
    try {
      const endpoint = format === 'docx' ? 'export/word' : 'export/pdf';
      const res = await fetch(`${API}/${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ content: responseText, title, format }),
      });
      if (!res.ok) throw new Error('Export failed');
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${title.replace(/\s+/g, '_')}.${format === 'docx' ? 'docx' : 'pdf'}`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Export error:', err);
    }
  };

  const handleCreateMatter = async () => {
    const name = prompt('Enter matter name:');
    if (!name) return;
    try {
      const res = await fetch(`${API}/matters`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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

  return (
    <div className="flex flex-col h-full" data-testid="assistant-page">
      {/* Top Bar */}
      <div className="h-14 border-b border-[#E2E8F0] px-6 flex items-center justify-between shrink-0 bg-white">
        <div className="flex items-center gap-4">
          {/* Matter Selector */}
          <div className="relative">
            <button
              onClick={() => setShowMatterDropdown(!showMatterDropdown)}
              className="flex items-center gap-2 px-3 py-1.5 border border-[#E2E8F0] rounded-sm text-sm hover:bg-[#F8FAFC] transition-colors"
              data-testid="matter-selector"
            >
              <FileText className="w-3.5 h-3.5 text-[#64748B]" />
              <span className="text-[#0D0D0D] font-medium">
                {selectedMatter ? matters.find(m => m.matter_id === selectedMatter)?.name || 'Select Matter' : 'New Query'}
              </span>
              <ChevronDown className="w-3 h-3 text-[#64748B]" />
            </button>
            {showMatterDropdown && (
              <div className="absolute top-full left-0 mt-1 w-64 bg-white border border-[#E2E8F0] rounded-sm shadow-[0_4px_16px_rgba(0,0,0,0.08)] z-50">
                <button
                  onClick={() => { setSelectedMatter(''); setShowMatterDropdown(false); }}
                  className="w-full px-4 py-2 text-left text-sm text-[#4A4A4A] hover:bg-[#F8FAFC] flex items-center gap-2"
                  data-testid="new-query-option"
                >
                  <Sparkles className="w-3 h-3" /> New Query (No Matter)
                </button>
                {matters.map(m => (
                  <button
                    key={m.matter_id}
                    onClick={() => { setSelectedMatter(m.matter_id); setShowMatterDropdown(false); }}
                    className="w-full px-4 py-2 text-left text-sm text-[#0D0D0D] hover:bg-[#F8FAFC] truncate"
                  >
                    {m.name}
                  </button>
                ))}
                <div className="border-t border-[#E2E8F0]">
                  <button
                    onClick={handleCreateMatter}
                    className="w-full px-4 py-2 text-left text-sm text-[#1A1A2E] hover:bg-[#F8FAFC] flex items-center gap-2 font-medium"
                    data-testid="create-matter-btn"
                  >
                    <Plus className="w-3 h-3" /> Create New Matter
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Mode Toggle */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setMode(mode === 'partner' ? 'everyday' : 'partner')}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-sm text-sm font-medium transition-colors ${
              mode === 'partner'
                ? 'bg-[#1A1A2E] text-white'
                : 'bg-[#F0FDF4] text-[#166534] border border-[#BBF7D0]'
            }`}
            data-testid="mode-toggle"
          >
            {mode === 'partner' ? (
              <><Scale className="w-3.5 h-3.5" /> Partner Mode</>
            ) : (
              <><Sparkles className="w-3.5 h-3.5" /> Everyday Mode</>
            )}
          </button>
        </div>
      </div>

      {/* Conversation Area */}
      <div className="flex-1 overflow-y-auto px-6 py-6" data-testid="conversation-area">
        {conversations.length === 0 && (
          <div className="max-w-3xl mx-auto pt-16 text-center">
            <div className="w-12 h-12 bg-[#F8FAFC] border border-[#E2E8F0] rounded-sm flex items-center justify-center mx-auto mb-6">
              <Scale className="w-6 h-6 text-[#1A1A2E]" />
            </div>
            <h2 className="text-2xl font-bold text-[#1A1A2E] tracking-tight mb-2">
              Associate is ready.
            </h2>
            <p className="text-sm text-[#64748B] mb-8 max-w-lg mx-auto">
              Query Indian law with precision. Every response is structured as a senior partner's memo
              with exact citations, case law, and rupee calculations.
            </p>
            <div className="grid grid-cols-2 gap-3 max-w-xl mx-auto">
              {[
                'What are the grounds to challenge a GST SCN for ITC mismatch?',
                'Draft a Section 138 cheque bounce notice for ₹15 lakhs',
                'Can a director be held liable under Section 141 NI Act?',
                'What is the limitation period for filing under Section 34 of the Arbitration Act?',
              ].map((q, i) => (
                <button
                  key={i}
                  onClick={() => { setQuery(q); inputRef.current?.focus(); }}
                  className="text-left p-3 border border-[#E2E8F0] rounded-sm text-sm text-[#4A4A4A] hover:bg-[#F8FAFC] hover:border-[#CBD5E1] transition-colors"
                  data-testid={`suggested-query-${i}`}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="max-w-4xl mx-auto space-y-6">
          {conversations.map((conv, i) => {
            if (conv.type === 'query') {
              return (
                <div key={i} className="flex justify-end animate-fade-in-up">
                  <div className="bg-[#F8FAFC] border border-[#E2E8F0] rounded-sm px-4 py-3 max-w-2xl">
                    <p className="text-[15px] text-[#0D0D0D]">{conv.text}</p>
                    <p className="text-[10px] text-[#94A3B8] mt-1 font-mono">
                      {new Date(conv.timestamp).toLocaleTimeString()}
                    </p>
                  </div>
                </div>
              );
            }
            if (conv.type === 'response') {
              return (
                <div key={i} className="animate-fade-in-up">
                  <ResponseCard
                    sections={conv.data.sections}
                    sources={conv.data.sources}
                    modelUsed={conv.data.model_used}
                    citationsCount={conv.data.citations_count}
                    onExport={(format) => handleExport(format, conv.data.response_text)}
                    onDraft={() => {
                      setQuery(`Draft a formal document based on: ${conversations[i-1]?.text || 'the previous analysis'}`);
                      inputRef.current?.focus();
                    }}
                  />
                </div>
              );
            }
            if (conv.type === 'error') {
              return (
                <div key={i} className="bg-[#FEF2F2] border border-[#FECACA] rounded-sm p-4 text-sm text-[#991B1B]">
                  {conv.text}
                </div>
              );
            }
            return null;
          })}

          {loading && (
            <div className="animate-fade-in-up">
              <div className="border border-[#E2E8F0] rounded-sm p-6 bg-white">
                <div className="flex items-center gap-3 mb-3">
                  <Loader2 className="w-4 h-4 text-[#1A1A2E] animate-spin" />
                  <span className="text-xs font-semibold tracking-wider text-[#64748B] uppercase">Associate is analyzing...</span>
                </div>
                <div className="space-y-2">
                  <div className="h-3 bg-[#F1F5F9] rounded-sm w-full animate-pulse" />
                  <div className="h-3 bg-[#F1F5F9] rounded-sm w-4/5 animate-pulse" />
                  <div className="h-3 bg-[#F1F5F9] rounded-sm w-3/5 animate-pulse" />
                </div>
                <div className="flex items-center gap-4 mt-4 text-[10px] text-[#94A3B8] font-mono">
                  <span>Fetching from IndianKanoon...</span>
                  <span>Searching statute DB...</span>
                  <span>Reasoning with Claude...</span>
                </div>
              </div>
            </div>
          )}
          <div ref={responseEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className="border-t border-[#E2E8F0] px-6 py-4 bg-white shrink-0" data-testid="query-input-area">
        <form onSubmit={handleSubmit} className="max-w-4xl mx-auto">
          <div className="flex items-end gap-3">
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSubmit(e);
                  }
                }}
                placeholder="Query Indian law — Section 138 notice, GST SCN defence, limitation period..."
                className="w-full resize-none border border-[#E2E8F0] rounded-sm px-4 py-3 text-[15px] text-[#0D0D0D] placeholder:text-[#94A3B8] focus:outline-none focus:ring-1 focus:ring-[#0D0D0D] focus:border-[#0D0D0D] transition-all min-h-[48px] max-h-[200px]"
                rows={1}
                data-testid="query-input"
              />
            </div>
            <button
              type="submit"
              disabled={!query.trim() || loading}
              className="bg-[#1A1A2E] text-white p-3 rounded-sm hover:bg-[#0D0D0D] transition-colors disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
              data-testid="submit-query-btn"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
          <div className="flex items-center justify-between mt-2">
            <p className="text-[10px] text-[#94A3B8] font-mono">
              Shift+Enter for new line | {mode === 'partner' ? 'Partner' : 'Everyday'} Mode active
            </p>
          </div>
        </form>
      </div>
    </div>
  );
}
