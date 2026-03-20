import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import ResponseCard from '../components/ResponseCard';
import {
  History, Clock, Filter, Search, FileText, Scale, Calculator, ChevronRight, Eye
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function HistoryPage() {
  const { user } = useAuth();
  const [history, setHistory] = useState([]);
  const [selectedItem, setSelectedItem] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState('all');

  useEffect(() => { fetchHistory(); }, []);

  const fetchHistory = async () => {
    try {
      const res = await fetch(`${API}/history`, { credentials: 'include' });
      if (res.ok) setHistory(await res.json());
    } catch {}
  };

  const filtered = history.filter(h => {
    const matchesSearch = h.query.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesType = filterType === 'all' || h.query_types?.includes(filterType);
    return matchesSearch && matchesType;
  });

  const getTypeIcon = (types) => {
    if (types?.includes('financial')) return <Calculator className="w-3.5 h-3.5 text-[#B45309]" />;
    if (types?.includes('legal')) return <Scale className="w-3.5 h-3.5 text-[#1A1A2E]" />;
    return <FileText className="w-3.5 h-3.5 text-[#64748B]" />;
  };

  return (
    <div className="flex flex-col h-full" data-testid="history-page">
      <div className="h-14 border-b border-[#E2E8F0] px-6 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <History className="w-4 h-4 text-[#64748B]" />
          <h1 className="text-base font-semibold text-[#1A1A2E]">History & Audit</h1>
          <span className="text-xs text-[#64748B] font-mono ml-2">{history.length} queries</span>
        </div>
        <div className="flex items-center gap-2">
          {['all', 'legal', 'financial', 'corporate', 'compliance'].map((t) => (
            <button
              key={t}
              onClick={() => setFilterType(t)}
              className={`px-2.5 py-1 text-[10px] font-medium rounded-sm transition-colors uppercase tracking-wider ${
                filterType === t ? 'bg-[#1A1A2E] text-white' : 'text-[#64748B] hover:bg-[#F8FAFC]'
              }`}
              data-testid={`filter-${t}`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* List */}
        <div className="w-[400px] border-r border-[#E2E8F0] flex flex-col shrink-0">
          <div className="p-3">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-[#94A3B8] absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search history..."
                className="w-full pl-9 pr-3 py-2 text-sm border border-[#E2E8F0] rounded-sm focus:outline-none focus:ring-1 focus:ring-[#0D0D0D]"
                data-testid="history-search"
              />
            </div>
          </div>

          <div className="flex-1 overflow-y-auto px-3 pb-3 space-y-1">
            {filtered.map((item) => (
              <div
                key={item.history_id}
                onClick={() => setSelectedItem(item)}
                className={`p-3 rounded-sm cursor-pointer transition-colors border ${
                  selectedItem?.history_id === item.history_id
                    ? 'border-[#1A1A2E] bg-[#F8FAFC]'
                    : 'border-transparent hover:bg-[#F8FAFC]'
                }`}
                data-testid={`history-item-${item.history_id}`}
              >
                <div className="flex items-start gap-2">
                  {getTypeIcon(item.query_types)}
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-[#0D0D0D] line-clamp-2">{item.query}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-[10px] font-mono text-[#64748B]">
                        {item.mode === 'partner' ? 'Partner' : 'Everyday'}
                      </span>
                      <span className="text-[10px] text-[#94A3B8]">
                        {item.citations_count || 0} citations
                      </span>
                      <span className="text-[10px] text-[#94A3B8] ml-auto font-mono">
                        {new Date(item.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
            {filtered.length === 0 && (
              <p className="text-sm text-[#94A3B8] text-center py-8">No history found</p>
            )}
          </div>
        </div>

        {/* Detail */}
        <div className="flex-1 overflow-y-auto p-6">
          {selectedItem ? (
            <div>
              <div className="mb-6">
                <h2 className="text-base font-semibold text-[#0D0D0D] mb-2">{selectedItem.query}</h2>
                <div className="flex items-center gap-3 text-xs text-[#64748B] font-mono">
                  <span>{selectedItem.model_used}</span>
                  <span>{selectedItem.mode} mode</span>
                  <span>{new Date(selectedItem.created_at).toLocaleString()}</span>
                  <span>{selectedItem.citations_count} citations</span>
                </div>
              </div>
              <ResponseCard
                sections={selectedItem.sections}
                sources={selectedItem.sources}
                modelUsed={selectedItem.model_used}
                citationsCount={selectedItem.citations_count}
              />
            </div>
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <Clock className="w-8 h-8 text-[#CBD5E1] mx-auto mb-3" />
                <p className="text-sm text-[#94A3B8]">Select a query to view full details</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
