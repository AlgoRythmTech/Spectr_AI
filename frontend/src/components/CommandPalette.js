import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search, MessageSquare, FolderOpen, Workflow, BookOpen, History,
  FileSpreadsheet, ArrowRight, Scale, Calculator, X, Command
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL ? `${process.env.REACT_APP_BACKEND_URL}/api` : '/api';

const QUICK_ACTIONS = [
  { id: 'assistant', label: 'Open Assistant', icon: MessageSquare, path: '/app/assistant', type: 'navigate' },
  { id: 'vault', label: 'Open Vault (The Box)', icon: FolderOpen, path: '/app/vault', type: 'navigate' },
  { id: 'workflows', label: 'Open Workflows', icon: Workflow, path: '/app/workflows', type: 'navigate' },
  { id: 'library', label: 'Open Library', icon: BookOpen, path: '/app/library', type: 'navigate' },
  { id: 'history', label: 'Open History', icon: History, path: '/app/history', type: 'navigate' },
  { id: 'reconciler', label: 'GSTR-2B Reconciler', icon: FileSpreadsheet, path: '/app/reconciler', type: 'navigate' },
  { id: 'cheque_bounce', label: 'Draft: Cheque Bounce Notice (Sec 138)', icon: Scale, path: '/app/workflows', type: 'workflow', workflowId: 'cheque_bounce_notice' },
  { id: 'bail', label: 'Draft: Bail Application', icon: Scale, path: '/app/workflows', type: 'workflow', workflowId: 'bail_application' },
  { id: 'anticipatory_bail', label: 'Draft: Anticipatory Bail (Sec 438)', icon: Scale, path: '/app/workflows', type: 'workflow', workflowId: 'anticipatory_bail' },
  { id: 'gst_scn', label: 'Draft: GST SCN Response', icon: Calculator, path: '/app/workflows', type: 'workflow', workflowId: 'gst_scn_response' },
  { id: 'it_143', label: 'Draft: IT Notice Reply (Sec 143)', icon: Calculator, path: '/app/workflows', type: 'workflow', workflowId: 'it_notice_143' },
  { id: 'it_148', label: 'Draft: IT Notice Reply (Sec 148)', icon: Calculator, path: '/app/workflows', type: 'workflow', workflowId: 'it_notice_148' },
  { id: 'writ', label: 'Draft: Writ Petition (HC)', icon: Scale, path: '/app/workflows', type: 'workflow', workflowId: 'writ_petition' },
  { id: 'recovery', label: 'Draft: Recovery Suit (Order XXXVII)', icon: Scale, path: '/app/workflows', type: 'workflow', workflowId: 'recovery_suit_o37' },
  { id: 'fema', label: 'Draft: FEMA Compounding', icon: Calculator, path: '/app/workflows', type: 'workflow', workflowId: 'fema_compounding' },
  { id: 'ibc', label: 'Draft: IBC Section 9 Application', icon: Scale, path: '/app/workflows', type: 'workflow', workflowId: 'ibc_section9' },
];

export default function CommandPalette({ isOpen, onClose }) {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [searchResults, setSearchResults] = useState([]);
  const inputRef = useRef(null);
  const navigate = useNavigate();

  const filtered = query.trim()
    ? QUICK_ACTIONS.filter(a =>
        a.label.toLowerCase().includes(query.toLowerCase())
      )
    : QUICK_ACTIONS.slice(0, 8);

  const allResults = [...filtered, ...searchResults];

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
      setQuery('');
      setSelectedIndex(0);
      setSearchResults([]);
    }
  }, [isOpen]);

  // Debounced search for vault documents and library items
  useEffect(() => {
    if (!query.trim() || query.length < 3) {
      setSearchResults([]);
      return;
    }
    const timer = setTimeout(async () => {
      try {
        const res = await fetch(`${API}/search?q=${encodeURIComponent(query)}`, { credentials: 'include' });
        if (res.ok) {
          const data = await res.json();
          setSearchResults(data.map(item => ({
            id: `search_${item.id}`,
            label: item.title || item.name,
            icon: item.type === 'vault' ? FolderOpen : BookOpen,
            path: item.type === 'vault' ? '/app/vault' : '/app/library',
            type: 'navigate',
            subtitle: item.type
          })));
        }
      } catch {}
    }, 300);
    return () => clearTimeout(timer);
  }, [query]);

  const handleSelect = useCallback((item) => {
    onClose();
    navigate(item.path);
  }, [navigate, onClose]);

  const handleKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(i => Math.min(i + 1, allResults.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(i => Math.max(i - 1, 0));
    } else if (e.key === 'Enter' && allResults[selectedIndex]) {
      handleSelect(allResults[selectedIndex]);
    } else if (e.key === 'Escape') {
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[9999] flex items-start justify-center pt-[15vh]" data-testid="command-palette">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />

      {/* Palette */}
      <div className="relative w-[640px] rounded-[16px] shadow-2xl border border-[#E2E8F0] overflow-hidden animate-fade-in-up" style={{ background: 'rgba(255,255,255,0.9)', backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)' }}>
        {/* Search Input */}
        <div className="flex items-center gap-3 px-5 py-4 border-b border-[#E2E8F0]">
          <Search className="w-5 h-5 text-[#94A3B8] shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => { setQuery(e.target.value); setSelectedIndex(0); }}
            onKeyDown={handleKeyDown}
            placeholder="Search commands, documents, workflows..."
            className="flex-1 text-[15px] text-[#0D0D0D] placeholder:text-[#94A3B8] outline-none bg-transparent"
            data-testid="command-input"
          />
          <kbd className="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-mono text-[#94A3B8] bg-[#F1F5F9] border border-[#E2E8F0] rounded">
            ESC
          </kbd>
        </div>

        {/* Results */}
        <div className="max-h-[400px] overflow-y-auto py-2">
          {query.trim() === '' && (
            <div className="px-5 py-1.5">
              <p className="text-[10px] font-bold text-[#94A3B8] uppercase tracking-widest">Quick Actions</p>
            </div>
          )}
          {allResults.map((item, idx) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                onClick={() => handleSelect(item)}
                className={`w-full flex items-center gap-3 px-5 py-2.5 text-left transition-colors rounded-[10px] mx-2 ${
                  idx === selectedIndex
                    ? 'bg-[#0A0A0A] text-white'
                    : 'text-[#0D0D0D] hover:bg-white/60'
                }`}
                data-testid={`cmd-${item.id}`}
              >
                <Icon className={`w-4 h-4 shrink-0 ${idx === selectedIndex ? 'text-white' : 'text-[#64748B]'}`} />
                <div className="flex-1 min-w-0">
                  <p className={`text-sm font-medium truncate ${idx === selectedIndex ? 'text-white' : ''}`}>
                    {item.label}
                  </p>
                  {item.subtitle && (
                    <p className={`text-[10px] ${idx === selectedIndex ? 'text-white/70' : 'text-[#94A3B8]'}`}>
                      {item.subtitle}
                    </p>
                  )}
                </div>
                <ArrowRight className={`w-3 h-3 shrink-0 ${idx === selectedIndex ? 'text-white/70' : 'text-[#CBD5E1]'}`} />
              </button>
            );
          })}
          {query.trim() && allResults.length === 0 && (
            <div className="px-5 py-8 text-center">
              <p className="text-sm text-[#94A3B8]">No results for "{query}"</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-[#E2E8F0] px-5 py-2.5 flex items-center justify-between">
          <div className="flex items-center gap-3 text-[10px] text-[#94A3B8] font-mono">
            <span>↑↓ Navigate</span>
            <span>↵ Select</span>
            <span>ESC Close</span>
          </div>
          <div className="flex items-center gap-1 text-[10px] text-[#94A3B8] font-mono">
            <Command className="w-3 h-3" /> <span>Ctrl+K</span>
          </div>
        </div>
      </div>
    </div>
  );
}
