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
    <div className="flex flex-col h-full bg-[#FFFFFF] font-sans page-bg">
      <div className="h-16 border-b border-[#E8ECF1] px-8 flex items-center gap-3 shrink-0 bg-[#FFFFFF] glass-header">
        <div className="w-9 h-9 bg-[#F5F5F5] rounded-lg flex items-center justify-center">
          <Scale className="w-[18px] h-[18px] text-[#000]" />
        </div>
        <div>
          <h1 className="text-[17px] font-bold text-[#0A0A0A] tracking-tight leading-tight">Case Finder</h1>
          <p className="text-[11px] text-[#64748B]">Search IndianKanoon with AI-powered query formulation</p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-8">
        <div className="max-w-[1000px] mx-auto page-enter">

          <div className="mb-8">
            <h2 className="text-[24px] font-bold text-[#111827] mb-3 tracking-[-0.02em]">Find Relevant Precedents</h2>
            <p className="text-[14px] text-[#6B7280] max-w-[600px] leading-relaxed">
              Describe your factual scenario or legal issue. Associate formulates search queries, scans IndianKanoon, and ranks the most relevant judgments with targeted holdings.
            </p>
          </div>

          <div className="glass-card-static p-6 mb-8">
            <form onSubmit={handleSearch}>
              <textarea
                value={scenario}
                onChange={(e) => setScenario(e.target.value)}
                placeholder="e.g. A vendor supplied goods without an e-way bill. The officer detained the vehicle under Section 129 but issued notice after 7 days..."
                className="w-full h-32 p-4 text-[14.5px] glass-input resize-none mb-4 leading-relaxed"
              />
              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={loading || !scenario.trim()}
                  className="bg-[#000] text-white px-6 py-3 btn-black-pill font-semibold flex items-center gap-2 hover:bg-[#1f2937] transition-all disabled:opacity-50"
                >
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                  Identify Precedents
                </button>
              </div>
            </form>
          </div>

          {loading && (
            <div className="text-center py-16">
              <Loader2 className="w-8 h-8 text-[#0A0A0A] animate-spin mx-auto mb-4" />
              <p className="text-[#4B5563] text-[13px] font-semibold">Searching IndianKanoon and ranking results...</p>
            </div>
          )}

          {!loading && results.length > 0 && (
            <div className="space-y-4 stagger-children">
              <h3 className="text-[14px] font-bold text-[#111827] tracking-wider uppercase mb-6 flex items-center gap-2">
                <Bookmark className="w-4 h-4" /> Ranked Results ({results.length})
              </h3>
              
              {results.map((result, idx) => (
                <div key={idx} className="glass-card p-6 flex gap-6">
                  
                  {/* Score */}
                  <div className="flex flex-col items-center justify-center shrink-0">
                    <div className="w-14 h-14 rounded-full border-4 flex items-center justify-center text-[15px] font-bold" 
                      style={{ 
                        borderColor: result.relevance_score > 80 ? '#000' : result.relevance_score > 50 ? '#999' : '#666',
                        color: result.relevance_score > 80 ? '#0A0A0A' : result.relevance_score > 50 ? '#333' : '#333',
                        background: result.relevance_score > 80 ? '#F0F0F0' : result.relevance_score > 50 ? '#F5F5F5' : '#F5F5F5'
                      }}>
                      {result.relevance_score}
                    </div>
                    <span className="text-[10px] text-[#6B7280] font-mono uppercase mt-2 font-bold tracking-widest">Match</span>
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <a href={result.url} target="_blank" rel="noreferrer" className="text-[16px] font-bold text-[#000] hover:underline block truncate mb-1">
                      {result.title}
                    </a>
                    <div className="text-[12px] text-[#6B7280] font-mono mb-3 bg-[#F3F4F6] inline-block px-2 py-0.5 rounded">
                       {result.docsource || 'IndianKanoon'}
                    </div>
                    
                    <p className="text-[14px] text-[#111827] leading-relaxed mb-4 bg-[#FAFAFA] p-3 border-l-2 border-[#000] font-medium">
                      <span className="text-[#0A0A0A] font-bold text-[11px] uppercase tracking-wider block mb-1">Targeted Holding</span>
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
                       className="w-full text-center py-2 px-3 bg-[#FAFAFA] border border-[#D1D5DB] rounded-[100px] text-[12px] font-semibold text-[#374151] hover:bg-[#F3F4F6] transition-all flex items-center justify-center gap-1"
                     >
                       Read Full <ChevronRight className="w-3 h-3" />
                     </a>
                     <button
                       onClick={() => handleCopy(`${result.title} [${result.url}]`, idx)}
                       className="w-full text-center py-2 px-3 bg-[#FAFAFA] border border-[#D1D5DB] rounded-[100px] text-[12px] font-semibold text-[#374151] hover:bg-[#F3F4F6] transition-all flex items-center justify-center gap-1"
                     >
                       {copiedLink === idx ? <Check className="w-3 h-3 text-[#000]" /> : <Copy className="w-3 h-3" />}
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
