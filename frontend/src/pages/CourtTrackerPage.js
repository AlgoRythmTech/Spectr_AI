import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { Briefcase, Plus, Loader2, RefreshCw, Trash2, Calendar, Scale, ChevronRight } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL ? `${process.env.REACT_APP_BACKEND_URL}/api` : '/api';

export default function CourtTrackerPage() {
  const { getToken } = useAuth();
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [refreshing, setRefreshing] = useState(null);

  const [newCase, setNewCase] = useState({ case_number: '', court: 'supreme_court', party_name: '' });

  useEffect(() => {
    fetchCases();
  }, []);

  const fetchCases = async () => {
    setLoading(true);
    try {
      const token = await getToken();
      const res = await fetch(`${API}/court/upcoming`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setCases(data.cases || []);
      }
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  };

  const handleAddCase = async (e) => {
    e.preventDefault();
    if (!newCase.case_number && !newCase.party_name) return;
    
    setAdding(true);
    try {
      const token = await getToken();
      const res = await fetch(`${API}/court/track`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(newCase)
      });
      if (res.ok) {
        setNewCase({ case_number: '', court: 'supreme_court', party_name: '' });
        await fetchCases();
      }
    } catch (err) {
      console.error(err);
    }
    setAdding(false);
  };

  const handleRemove = async (trackId) => {
    try {
      const token = await getToken();
      await fetch(`${API}/court/track/${trackId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      setCases(cases.filter(c => c.track_id !== trackId));
    } catch (err) {
      console.error(err);
    }
  };

  const handleRefresh = async (trackId) => {
    setRefreshing(trackId);
    try {
      const token = await getToken();
      const res = await fetch(`${API}/court/refresh/${trackId}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const updated = await res.json();
        setCases(cases.map(c => c.track_id === trackId ? updated : c));
      }
    } catch (err) {
      console.error(err);
    }
    setRefreshing(null);
  };

  return (
    <div className="flex flex-col h-full bg-[#FFFFFF] font-sans page-bg">
      <div className="h-16 border-b border-[#E8ECF1] px-8 flex items-center gap-3 shrink-0 bg-[#FFFFFF] glass-header">
        <div className="w-9 h-9 bg-[#F0F0F0] rounded-lg flex items-center justify-center">
          <Briefcase className="w-[18px] h-[18px] text-[#0A0A0A]" />
        </div>
        <div>
          <h1 className="text-[17px] font-bold text-[#0A0A0A] tracking-tight leading-tight">Court Tracker</h1>
          <p className="text-[11px] text-[#64748B]">Track cases across Supreme Court, High Courts, NCLT &amp; tribunals</p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-8">
        <div className="max-w-[1000px] mx-auto">
          
          <div className="glass-card-static p-6 mb-8">
            <h2 className="text-[16px] font-bold text-[#111827] mb-4">Track New Matter</h2>
            <form onSubmit={handleAddCase} className="flex gap-4 items-end">
              <div className="flex-1">
                <label className="block text-[12px] font-bold text-[#4B5563] uppercase tracking-wider mb-2">Case Number / Diary Nu.</label>
                <input
                  type="text"
                  value={newCase.case_number}
                  onChange={(e) => setNewCase({...newCase, case_number: e.target.value})}
                  placeholder="e.g. SLP(C) No. 1234/2026"
                  className="w-full p-3 text-[14px] glass-input"
                />
              </div>
              <div className="flex-1">
                <label className="block text-[12px] font-bold text-[#4B5563] uppercase tracking-wider mb-2">Party Name</label>
                <input
                  type="text"
                  value={newCase.party_name}
                  onChange={(e) => setNewCase({...newCase, party_name: e.target.value})}
                  placeholder="e.g. Union of India vs X"
                  className="w-full p-3 text-[14px] glass-input"
                />
              </div>
              <div className="w-48">
                <label className="block text-[12px] font-bold text-[#4B5563] uppercase tracking-wider mb-2">Court</label>
                <select
                  value={newCase.court}
                  onChange={(e) => setNewCase({...newCase, court: e.target.value})}
                  className="w-full p-3 text-[14px] glass-input bg-white"
                >
                  <option value="supreme_court">Supreme Court</option>
                  <option value="high_court">High Court</option>
                  <option value="delhi_hc">Delhi HC</option>
                  <option value="bombay_hc">Bombay HC</option>
                  <option value="nclt">NCLT / NCLAT</option>
                  <option value="cestat">CESTAT</option>
                </select>
              </div>
              <button
                type="submit"
                disabled={adding || (!newCase.case_number && !newCase.party_name)}
                className="bg-[#000] text-white px-6 py-3 btn-black-pill font-semibold flex items-center justify-center gap-2 hover:bg-[#1f2937] transition-all disabled:opacity-50 h-[46px] w-[140px]"
              >
                {adding ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                Track
              </button>
            </form>
          </div>

          <h2 className="text-[16px] font-bold text-[#111827] mb-6">Active Trackers ({cases.length})</h2>

          {loading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="w-8 h-8 text-[#000] animate-spin" />
            </div>
          ) : cases.length === 0 ? (
            <div className="text-center py-12 bg-[#FAFAFA] border border-dashed border-[#D1D5DB] rounded-[16px]">
              <p className="text-[#6B7280] text-[14px]">No cases tracked yet. Add one above to fetch details from eCourts/NJDG.</p>
            </div>
          ) : (
            <div className="grid gap-6 grid-cols-1 stagger-children">
              {cases.map((c) => (
                <div key={c.track_id} className="glass-card p-6 flex flex-col gap-4">
                  
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="flex items-center gap-2 mb-2">
                         <span className="text-[11px] font-bold text-[#374151] bg-[#F3F4F6] px-2 py-1 rounded inline-block uppercase tracking-wider">{c.court.replace('_', ' ')}</span>
                      </div>
                      <h3 className="text-[18px] font-bold text-[#111827]">{c.case_number || c.party_name}</h3>
                      {c.party_name && c.case_number && <p className="text-[14px] text-[#4B5563] mt-1">{c.party_name}</p>}
                    </div>
                    
                    <div className="flex gap-2">
                       <button onClick={() => handleRefresh(c.track_id)} className="p-2 text-[#4B5563] hover:text-[#000] bg-[#F9FAFB] hover:bg-[#F3F4F6] border border-[#E5E7EB] rounded transition-all focus:outline-none" title="Refresh eCourts Data">
                         <RefreshCw className={`w-4 h-4 ${refreshing === c.track_id ? 'animate-spin' : ''}`} />
                       </button>
                       <button onClick={() => handleRemove(c.track_id)} className="p-2 text-[#666] hover:text-[#000] bg-[#FAFAFA] hover:bg-[#F5F5F5] border border-[#E5E5E5] rounded transition-all focus:outline-none" title="Stop Tracking">
                         <Trash2 className="w-4 h-4" />
                       </button>
                    </div>
                  </div>

                  <div className="border-t border-[#F3F4F6] pt-4">
                     <h4 className="text-[12px] font-bold text-[#6B7280] uppercase tracking-wider mb-3">Live Status & Scrape Results</h4>
                     {c.search_results && c.search_results.length > 0 ? (
                       <ul className="space-y-4">
                         {c.search_results.map((res, i) => (
                           <li key={i} className="flex gap-3">
                             <div className="mt-1 flex-shrink-0">
                               {res.source === 'IndianKanoon' ? <Scale className="w-4 h-4 text-[#333]" /> : <Calendar className="w-4 h-4 text-[#000]" />}
                             </div>
                             <div>
                               <a href={res.url} target="_blank" rel="noreferrer" className="text-[14px] font-semibold text-[#111827] hover:underline flex items-center gap-1">
                                 {res.title} <ChevronRight className="w-3 h-3 text-[#9CA3AF]" />
                               </a>
                               {res.snippet && <p className="text-[13px] text-[#4B5563] mt-1 leading-relaxed line-clamp-2">{res.snippet}</p>}
                               <span className="text-[10px] uppercase font-bold text-[#9CA3AF] tracking-wider mt-1 block">{res.source}</span>
                             </div>
                           </li>
                         ))}
                       </ul>
                     ) : (
                       <p className="text-[13px] text-[#9CA3AF] italic">No digital records found yet. Will keep monitoring.</p>
                     )}
                     <div className="mt-4 text-[11px] text-[#9CA3AF] font-mono">
                       Last sync: {new Date(c.last_checked).toLocaleString()}
                     </div>
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
