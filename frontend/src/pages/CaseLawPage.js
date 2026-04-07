import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Scale, Search, Loader2, Bookmark, Copy, Check, ChevronRight } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL ? `${process.env.REACT_APP_BACKEND_URL}/api` : '/api';

export default function CaseLawPage() {
  const { getToken } = useAuth();
  const [scenario, setScenario] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState([]);
  const [copiedLink, setCopiedLink] = useState(null);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!scenario.trim()) return;
    
    setLoading(true);
    setResults([]);
    
    try {
      const token = await getToken();
      const res = await fetch(`${API}/caselaw/find`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        credentials: 'include',
        body: JSON.stringify({ scenario })
      });
      
      if (res.ok) {
        const data = await res.json();
        setResults(data.results || []);
      }
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  };

  const handleCopy = (text, index) => {
    navigator.clipboard.writeText(text);
    setCopiedLink(index);
    setTimeout(() => setCopiedLink(null), 2000);
  };

  return (
    <div className="flex flex-col h-full bg-[#FAFAFA] font-sans">
      <div className="h-16 border-b border-[#E5E7EB] px-8 flex items-center shrink-0 bg-[#FFFFFF]">
        <Scale className="w-5 h-5 text-[#000] mr-3" />
        <h1 className="text-[15px] font-semibold text-[#000] tracking-tight">Case Finder Intelligence</h1>
      </div>

      <div className="flex-1 overflow-y-auto p-8">
        <div className="max-w-[1000px] mx-auto">
          
          <div className="mb-10 text-center">
            <h2 className="text-[32px] font-bold text-[#111827] mb-4 tracking-[-0.02em]">Semantic Precedent Search</h2>
            <p className="text-[15px] text-[#4B5563] max-w-[600px] mx-auto">
              Describe your specific factual scenario, legal issue, or defense strategy. Our AI will formulate Boolean queries, scan IndianKanoon, and rank the most analogous judgments.
            </p>
          </div>

          <div className="bg-[#FFFFFF] border border-[#E5E7EB] rounded-[16px] p-6 shadow-sm mb-8">
            <form onSubmit={handleSearch}>
              <textarea
                value={scenario}
                onChange={(e) => setScenario(e.target.value)}
                placeholder="e.g. A vendor supplied goods without an e-way bill. The officer detained the vehicle under Section 129 but issued notice after 7 days..."
                className="w-full h-32 p-4 text-[14.5px] border border-[#D1D5DB] rounded-[8px] focus:outline-none focus:border-[#000] focus:ring-1 focus:ring-[#000] resize-none mb-4 leading-relaxed"
              />
              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={loading || !scenario.trim()}
                  className="bg-[#000] text-white px-6 py-3 rounded-[8px] font-semibold flex items-center gap-2 hover:bg-[#1f2937] transition-all disabled:opacity-50"
                >
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                  Identify Precedents
                </button>
              </div>
            </form>
          </div>

          {loading && (
            <div className="text-center py-16">
              <Loader2 className="w-8 h-8 text-[#000] animate-spin mx-auto mb-4" />
              <p className="text-[#4B5563] font-mono text-[13px] font-bold tracking-widest uppercase">Executing Multi-Query Search & Ranking...</p>
            </div>
          )}

          {!loading && results.length > 0 && (
            <div className="space-y-4">
              <h3 className="text-[14px] font-bold text-[#111827] tracking-wider uppercase mb-6 flex items-center gap-2">
                <Bookmark className="w-4 h-4" /> Ranked Results ({results.length})
              </h3>
              
              {results.map((result, idx) => (
                <div key={idx} className="bg-[#FFFFFF] border border-[#E5E7EB] rounded-[12px] p-6 hover:shadow-md transition-all flex gap-6">
                  
                  {/* Score */}
                  <div className="flex flex-col items-center justify-center shrink-0">
                    <div className="w-14 h-14 rounded-full border-4 flex items-center justify-center text-[15px] font-bold" 
                      style={{ 
                        borderColor: result.relevance_score > 80 ? '#10B981' : result.relevance_score > 50 ? '#F59E0B' : '#EF4444',
                        color: result.relevance_score > 80 ? '#065F46' : result.relevance_score > 50 ? '#92400E' : '#991B1B',
                        background: result.relevance_score > 80 ? '#D1FAE5' : result.relevance_score > 50 ? '#FEF3C7' : '#FEE2E2'
                      }}>
                      {result.relevance_score}
                    </div>
                    <span className="text-[10px] text-[#6B7280] font-mono uppercase mt-2 font-bold tracking-widest">Match</span>
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <a href={result.url} target="_blank" rel="noreferrer" className="text-[16px] font-bold text-[#1D4ED8] hover:underline block truncate mb-1">
                      {result.title}
                    </a>
                    <div className="text-[12px] text-[#6B7280] font-mono mb-3 bg-[#F3F4F6] inline-block px-2 py-0.5 rounded">
                       {result.docsource || 'IndianKanoon'}
                    </div>
                    
                    <p className="text-[14px] text-[#111827] leading-relaxed mb-4 bg-[#FAFAFA] p-3 border-l-2 border-[#10B981] font-medium">
                      <span className="text-[#059669] font-bold text-[11px] uppercase tracking-wider block mb-1">Targeted Holding</span>
                      {result.holding}
                    </p>

                    <p className="text-[13px] text-[#4B5563] leading-relaxed line-clamp-3">
                      <span dangerouslySetInnerHTML={{ __html: result.snippet }} />
                    </p>
                  </div>

                  {/* Actions */}
                  <div className="flex flex-col items-end gap-2 shrink-0 border-l border-[#F3F4F6] pl-4">
                     <a 
                       href={result.url} 
                       target="_blank" 
                       rel="noreferrer"
                       className="w-full text-center py-2 px-3 bg-[#FAFAFA] border border-[#D1D5DB] rounded-[6px] text-[12px] font-semibold text-[#374151] hover:bg-[#F3F4F6] transition-all flex items-center justify-center gap-1"
                     >
                       Read Full <ChevronRight className="w-3 h-3" />
                     </a>
                     <button
                       onClick={() => handleCopy(`${result.title} [${result.url}]`, idx)}
                       className="w-full text-center py-2 px-3 bg-[#FAFAFA] border border-[#D1D5DB] rounded-[6px] text-[12px] font-semibold text-[#374151] hover:bg-[#F3F4F6] transition-all flex items-center justify-center gap-1"
                     >
                       {copiedLink === idx ? <Check className="w-3 h-3 text-[#10B981]" /> : <Copy className="w-3 h-3" />}
                       Copy Cite
                     </button>
                  </div>

                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
