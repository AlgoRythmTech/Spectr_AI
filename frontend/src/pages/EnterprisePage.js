import React, { useState } from 'react';
import { getToken } from '../firebase';

const API = process.env.REACT_APP_BACKEND_URL ? `${process.env.REACT_APP_BACKEND_URL}/api` : '/api';

const EnterprisePage = () => {
    const [activeTab, setActiveTab] = useState('ledger'); // ledger, gst, notice
    const [file1, setFile1] = useState(null);
    const [file2, setFile2] = useState(null);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);

    const executeOperation = async () => {
        if (!file1) return alert("Please specify the primary file.");
        setLoading(true);
        setResult(null);
        
        try {
            const token = await getToken();
            const formData = new FormData();
            formData.append(activeTab === 'gst' ? 'pr_file' : 'file', file1);
            if (activeTab === 'gst' && file2) formData.append('gstr2b_file', file2);

            let endpoint = '';
            if (activeTab === 'ledger') endpoint = '/audit/ledger';
            if (activeTab === 'gst') endpoint = '/gst/reconcile';
            if (activeTab === 'notice') endpoint = '/vault/parse-notice';

            const res = await fetch(`${API}${endpoint}`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` },
                body: formData
            });

            if (!res.ok) throw new Error("Operation failed");
            const data = await res.json();
            setResult(data);
        } catch (e) {
            setResult({ error: e.message });
        }
        setLoading(false);
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: '#FFFFFF', padding: '32px' }}>
            <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 8, color: '#111827' }}>Enterprise Operations</h1>
            <p style={{ color: '#6B7280', fontSize: 14, marginBottom: 32 }}>Pandas-powered data-engineering modules operating continuously.</p>

            <div style={{ display: 'flex', gap: 16, marginBottom: 32, borderBottom: '1px solid #E5E7EB', paddingBottom: 16 }}>
                 <button onClick={() => {setActiveTab('ledger'); setResult(null);}} style={{ border: 'none', background: activeTab === 'ledger' ? '#111827' : 'transparent', color: activeTab === 'ledger' ? '#FFF' : '#6B7280', padding: '8px 16px', borderRadius: 4, cursor: 'pointer', fontWeight: 600 }}>Ledger Audit Engine</button>
                 <button onClick={() => {setActiveTab('gst'); setResult(null);}} style={{ border: 'none', background: activeTab === 'gst' ? '#111827' : 'transparent', color: activeTab === 'gst' ? '#FFF' : '#6B7280', padding: '8px 16px', borderRadius: 4, cursor: 'pointer', fontWeight: 600 }}>GSTR-2B vs PR Reconciler</button>
                 <button onClick={() => {setActiveTab('notice'); setResult(null);}} style={{ border: 'none', background: activeTab === 'notice' ? '#111827' : 'transparent', color: activeTab === 'notice' ? '#FFF' : '#6B7280', padding: '8px 16px', borderRadius: 4, cursor: 'pointer', fontWeight: 600 }}>Notice OCR Parser</button>
            </div>

            <div style={{ display: 'flex', gap: 24 }}>
                {/* File Inputs Panel */}
                <div style={{ flex: 1, padding: 24, border: '1px solid #E5E7EB', borderRadius: 8 }}>
                    <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>Upload Data</h3>
                    
                    <div style={{ marginBottom: 16 }}>
                        <label style={{ display: 'block', fontSize: 13, marginBottom: 8, color: '#374151', fontWeight: 600 }}>
                            {activeTab === 'ledger' ? 'Tally/SAP CSV Dump (.csv)' : activeTab === 'gst' ? 'Purchase Register (.xlsx)' : 'Notice PDF (.pdf)'}
                        </label>
                        <input type="file" onChange={e => setFile1(e.target.files[0])} style={{ width: '100%', padding: 8, border: '1px solid #D1D5DB', borderRadius: 4 }} />
                    </div>

                    {activeTab === 'gst' && (
                        <div style={{ marginBottom: 24 }}>
                             <label style={{ display: 'block', fontSize: 13, marginBottom: 8, color: '#374151', fontWeight: 600 }}>GSTR-2B JSON/Excel Export (.xlsx)</label>
                             <input type="file" onChange={e => setFile2(e.target.files[0])} style={{ width: '100%', padding: 8, border: '1px solid #D1D5DB', borderRadius: 4 }} />
                        </div>
                    )}

                    <button onClick={executeOperation} disabled={loading} style={{ width: '100%', padding: 12, background: '#111827', color: '#FFF', fontWeight: 600, border: 'none', borderRadius: 4, cursor: loading ? 'not-allowed' : 'pointer' }}>
                        {loading ? 'Executing Engine Operations...' : 'Run Operation'}
                    </button>
                </div>

                {/* Output Panel */}
                <div style={{ flex: 2, padding: 24, border: '1px solid #E5E7EB', borderRadius: 8, background: '#F9FAFB', overflowY: 'auto' }}>
                     <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>Data Matrix Output</h3>
                     {result ? (
                         <pre style={{ fontSize: 12, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{JSON.stringify(result, null, 2)}</pre>
                     ) : (
                         <div style={{ color: '#9CA3AF', fontSize: 13 }}>Awaiting execution...</div>
                     )}
                </div>
            </div>
        </div>
    );
};

export default EnterprisePage;
