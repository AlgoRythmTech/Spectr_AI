import React, { useState } from 'react';
import { Upload, FileDown, CheckCircle, AlertOctagon, ArrowRightLeft, FileSpreadsheet, KeySquare } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const API = process.env.REACT_APP_BACKEND_URL ? `${process.env.REACT_APP_BACKEND_URL}/api` : '/api';

export default function ReconcilerPage() {
  const { user } = useAuth();
  const [purchaseFile, setPurchaseFile] = useState(null);
  const [gstr2bFile, setGstr2bFile] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [result, setResult] = useState(null);

  const handleProcess = async () => {
    if (!purchaseFile || !gstr2bFile) return;
    setProcessing(true);
    setResult(null);

    const formData = new FormData();
    formData.append('purchase_file', purchaseFile);
    formData.append('gstr2b_file', gstr2bFile);

    try {
      const res = await fetch(`${API}/tools/reconcile-gstr2b`, {
        method: 'POST',
        credentials: 'include',
        body: formData
      });
      if (res.ok) {
        setResult(await res.json());
      } else {
        alert("Reconciliation failed. Check excel formats.");
      }
    } catch (err) {
      console.error(err);
      alert("Error reaching reconciliation engine.");
    }
    setProcessing(false);
  };

  return (
    <div className="flex flex-col h-full bg-[#FAFAFA]" data-testid="reconciler-page">
      {/* Top Header */}
      <div className="h-16 border-b border-[#E2E8F0] px-8 flex items-center justify-between shrink-0 bg-white shadow-sm z-10">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-[#F1F5F9] rounded-md border border-[#E2E8F0]">
            <ArrowRightLeft className="w-5 h-5 text-[#1A1A2E]" />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight text-[#1A1A2E]">GSTR-2B Auto-Reconciler</h1>
            <p className="text-xs text-[#64748B] font-medium mt-0.5 uppercase tracking-wider">CA Monopoly Engine • Fast Fuzzy Match</p>
          </div>
        </div>
      </div>

      <div className="p-8 flex-1 overflow-y-auto">
        {!result ? (
          <div className="max-w-4xl mx-auto space-y-6">
            <div className="grid grid-cols-2 gap-8">
              {/* Purchase Box */}
              <div className="bg-white border text-center p-8 border-[#E2E8F0] rounded-xl shadow-sm hover:border-[#CBD5E1] transition-colors h-64 flex flex-col justify-center">
                <FileSpreadsheet className="w-10 h-10 text-[#2563EB] mx-auto mb-3 opacity-80" />
                <h3 className="text-base font-bold text-[#1A1A2E] mb-1">Upload Purchase Register</h3>
                <p className="text-xs text-[#64748B] mb-4">(Client's Books / Tally Export)</p>
                <input 
                  type="file" 
                  accept=".xlsx, .xls, .csv" 
                  onChange={(e) => setPurchaseFile(e.target.files[0])}
                  className="block w-full text-xs text-[#64748B] file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-[#EFF6FF] file:text-[#2563EB] hover:file:bg-[#DBEAFE] transition-colors"
                />
              </div>

              {/* GSTR Box */}
              <div className="bg-white border text-center p-8 border-[#E2E8F0] rounded-xl shadow-sm hover:border-[#CBD5E1] transition-colors h-64 flex flex-col justify-center">
                <FileDown className="w-10 h-10 text-[#059669] mx-auto mb-3 opacity-80" />
                <h3 className="text-base font-bold text-[#1A1A2E] mb-1">Upload GSTR-2B</h3>
                <p className="text-xs text-[#64748B] mb-4">(Government Portal Export)</p>
                <input 
                  type="file" 
                  accept=".xlsx, .xls, .csv" 
                  onChange={(e) => setGstr2bFile(e.target.files[0])}
                  className="block w-full text-xs text-[#64748B] file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-[#ECFDF5] file:text-[#059669] hover:file:bg-[#D1FAE5] transition-colors"
                />
              </div>
            </div>

            <div className="flex justify-center pt-4">
              <button 
                onClick={handleProcess}
                disabled={processing || !purchaseFile || !gstr2bFile}
                className="bg-[#1A1A2E] text-white px-8 py-3 rounded-md font-semibold tracking-wide disabled:opacity-50 hover:bg-[#0D0D0D] transition-colors shadow-md"
              >
                {processing ? 'EXECUTING FUZZY RECONCILIATION...' : 'EXECUTE ITC RECONCILIATION'}
              </button>
            </div>
          </div>
        ) : (
          <div className="max-w-6xl mx-auto space-y-6">
            <button onClick={() => setResult(null)} className="text-[#64748B] hover:text-[#1A1A2E] text-sm font-medium mb-4 inline-flex items-center gap-1 transition-colors">
              ← Back to Upload
            </button>

            {/* Dashboard Stats */}
            <div className="grid grid-cols-4 gap-4">
              <div className="bg-white p-6 rounded-xl border border-[#E2E8F0] shadow-sm">
                <p className="text-[11px] font-bold text-[#64748B] uppercase tracking-wider mb-2">Total Invoices Evaluated</p>
                <p className="text-3xl font-black text-[#1A1A2E]">{result.total_invoices || 0}</p>
              </div>
              <div className="bg-white p-6 rounded-xl border border-[#10B981] shadow-sm bg-emerald-50/30">
                <p className="text-[11px] font-bold text-[#059669] uppercase tracking-wider mb-2">Perfect Matches (Pass 1)</p>
                <p className="text-3xl font-black text-[#059669]">{result.exact_matches || 0}</p>
              </div>
              <div className="bg-white p-6 rounded-xl border border-[#3B82F6] shadow-sm bg-blue-50/30">
                <p className="text-[11px] font-bold text-[#2563EB] uppercase tracking-wider mb-2">Fuzzy & LLM Matches</p>
                <p className="text-3xl font-black text-[#2563EB]">{result.fuzzy_matches || 0}</p>
              </div>
              <div className="bg-white p-6 rounded-xl border border-[#EF4444] shadow-sm bg-red-50/30">
                <p className="text-[11px] font-bold text-[#DC2626] uppercase tracking-wider mb-2">Likely Discrepancies (Notice Risk)</p>
                <p className="text-3xl font-black text-[#DC2626]">{result.discrepancies || 0}</p>
              </div>
            </div>

            {/* Details JSON output for now */}
            <div className="bg-white border border-[#E2E8F0] rounded-xl p-6 shadow-sm overflow-auto">
              <h3 className="font-bold text-[#1A1A2E] mb-4 flex items-center gap-2">
                <AlertOctagon className="w-5 h-5 text-[#DC2626]" /> 
                Discrepancy Matrix (Client Liability)
              </h3>
              <pre className="text-xs text-[#475569] bg-[#F8FAFC] p-4 rounded-md overflow-x-auto">
                {JSON.stringify(result.details || "No significant discrepancies found.", null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
