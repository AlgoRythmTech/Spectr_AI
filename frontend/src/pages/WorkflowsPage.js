import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import ResponseCard from '../components/ResponseCard';
import { useGoogleDriveConnection } from '../components/GoogleDriveConnect';
import { Search, X, Loader2, ArrowLeft, FileDown, FileText, FileSpreadsheet, ExternalLink } from 'lucide-react';

const API = process.env.NODE_ENV === 'development' ? '/api' : '/api';

const CATEGORY_LABELS = {
  litigation: 'Legal Drafting',
  taxation: 'Tax & Compliance',
  criminal: 'Criminal Law',
};

export default function WorkflowsPage() {
  const { getToken } = useAuth();
  const { status: driveStatus, connect: connectDrive } = useGoogleDriveConnection();
  const [templates, setTemplates] = useState([]);
  const [fetchLoading, setFetchLoading] = useState(true);
  const [activeCategory, setActiveCategory] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Workflow execution
  const [selected, setSelected] = useState(null);
  const [formData, setFormData] = useState({});
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [exporting, setExporting] = useState('');
  const [openingInDrive, setOpeningInDrive] = useState(false);

  useEffect(() => { fetchTemplates(); }, []); // eslint-disable-line

  const fetchTemplates = async () => {
    // /api/workflows is a public catalog — no auth header needed.
    // Sending dev_mock_token_7128 in dev mode works fine; the endpoint
    // doesn't require it. Omitting auth entirely for the catalog fetch
    // removes one possible failure mode (bad token → 401).
    try {
      let headers = {};
      try {
        const t = await getToken();
        if (t) headers.Authorization = `Bearer ${t}`;
      } catch {}
      const res = await fetch(`${API}/workflows`, { headers });
      console.log('[Workflows] fetch status:', res.status);
      if (res.ok) {
        const data = await res.json();
        console.log('[Workflows] received', Array.isArray(data) ? data.length : 'non-array', 'items');
        if (Array.isArray(data) && data.length > 0) setTemplates(data);
      } else {
        const body = await res.text().catch(() => '');
        console.error('[Workflows] fetch non-OK:', res.status, body.slice(0, 200));
      }
    } catch (err) {
      console.error('[Workflows] fetch threw:', err);
    }
    setFetchLoading(false);
  };

  const openWorkflow = (t) => {
    setSelected(t);
    setResult(null);
    setError('');
    // Initialize form with defaults
    const initial = {};
    (t.fields || []).forEach(f => { initial[f.name] = ''; });
    setFormData(initial);
  };

  const handleGenerate = async () => {
    if (!selected) return;
    setGenerating(true);
    setError('');
    try {
      let token = '';

      try { token = await getToken() || token; } catch { /**/ }
      try { token = await getToken() || token; } catch {}
      const res = await fetch(`${API}/workflows/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({
          workflow_type: selected.id,
          fields: formData,
          mode: 'partner',
        }),
      });
      if (!res.ok) {
        const errText = await res.text().catch(() => 'Generation failed');
        throw new Error(errText);
      }
      const data = await res.json();
      setResult(data);
    } catch (err) {
      setError(err.message || 'Something went wrong. Please try again.');
    }
    setGenerating(false);
  };

  const handleExport = async (format) => {
    if (!result?.response_text) return;
    setExporting(format);
    try {
      let token = '';

      try { token = await getToken() || token; } catch { /**/ }
      try { token = await getToken() || token; } catch {}
      const endpoint = format === 'docx' ? 'export/word' : 'export/pdf';
      const title = selected?.name || 'Document';
      const res = await fetch(`${API}/${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ content: result.response_text, title, format }),
      });
      if (!res.ok) throw new Error('Export failed');
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${title.replace(/\s+/g, '_')}.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Export error:', err);
    }
    setExporting('');
  };

  const handleOpenInGoogleDocs = async () => {
    if (!result?.docx_file_id) {
      setError('Document not ready for Drive upload. Please regenerate.');
      return;
    }
    if (!driveStatus.connected) {
      connectDrive();
      return;
    }
    setOpeningInDrive(true);
    setError('');
    try {
      let token = '';

      try { token = await getToken() || token; } catch { /**/ }
      try { token = await getToken() || token; } catch {}
      const fd = new FormData();
      fd.append('file_id', result.docx_file_id);
      fd.append('folder_id', 'root');
      fd.append('convert', 'true');
      const res = await fetch(`${API}/google/upload`, {
        method: 'POST',
        body: fd,
        headers: { 'Authorization': `Bearer ${token}` },
        credentials: 'include',
      });
      if (!res.ok) {
        const errText = await res.text().catch(() => 'Drive upload failed');
        throw new Error(errText);
      }
      const data = await res.json();
      if (data.drive_url) {
        window.open(data.drive_url, '_blank', 'noopener,noreferrer');
      } else {
        throw new Error('No Drive URL returned');
      }
    } catch (err) {
      setError(err.message || 'Could not open in Google Docs.');
    }
    setOpeningInDrive(false);
  };

  const goBack = () => {
    setSelected(null);
    setResult(null);
    setFormData({});
    setError('');
  };

  const categories = [...new Set(templates.map(t => t.category))];
  const filtered = templates.filter(t => {
    const matchCat = activeCategory === 'all' || t.category === activeCategory;
    const matchSearch = !searchQuery || t.name.toLowerCase().includes(searchQuery.toLowerCase());
    return matchCat && matchSearch;
  });
  const grouped = {};
  filtered.forEach(t => {
    const label = CATEGORY_LABELS[t.category] || t.category;
    if (!grouped[label]) grouped[label] = [];
    grouped[label].push(t);
  });

  /* ─── RENDER ─── */
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      fontFamily: "'Bricolage Grotesque', sans-serif", background: '#FFFFFF',
    }}>

      <style>{`
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        @keyframes slideUp { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
        .wf-card { transition: all 0.2s ease; }
        .wf-card:hover { border-color: #DDD !important; box-shadow: 0 4px 16px rgba(0,0,0,0.06) !important; transform: translateY(-2px) !important; }
        .export-btn { transition: all 0.15s ease; }
        .export-btn:hover { background: #F5F5F5 !important; border-color: #DDD !important; }
      `}</style>

      {/* Header */}
      <div style={{
        height: 52, padding: '0 32px',
        display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0,
        borderBottom: '1px solid #F2F2F2',
      }}>
        {selected && (
          <button onClick={goBack} style={{
            display: 'flex', alignItems: 'center', gap: 6, padding: '5px 10px',
            background: 'none', border: 'none', cursor: 'pointer', fontSize: 13,
            color: '#999', fontFamily: 'inherit', borderRadius: 7,
          }}>
            <ArrowLeft style={{ width: 14, height: 14 }} /> Back
          </button>
        )}
        <span style={{ fontSize: 14, fontWeight: 600, color: '#0A0A0A', letterSpacing: '-0.02em' }}>
          {selected ? selected.name : 'Workflows'}
        </span>
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: '28px 32px' }}>
        <div style={{ maxWidth: 900, margin: '0 auto' }}>

          {/* ═══ BROWSE STATE ═══ */}
          {!selected && (
            <>
              {/* Search */}
              <div style={{ marginBottom: 24 }}>
                <div style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  padding: '10px 14px', borderRadius: 12,
                  border: '1px solid #F0F0F0', background: '#fff',
                  marginBottom: 14,
                }}>
                  <Search style={{ width: 15, height: 15, color: '#CCC', flexShrink: 0 }} />
                  <input
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    placeholder={`Search ${templates.length} workflows...`}
                    style={{
                      flex: 1, border: 'none', outline: 'none', background: 'transparent',
                      fontSize: 14, color: '#0A0A0A', fontFamily: 'inherit',
                    }}
                  />
                  {searchQuery && (
                    <button onClick={() => setSearchQuery('')} style={{
                      background: 'none', border: 'none', cursor: 'pointer', padding: 0,
                      display: 'flex', color: '#CCC',
                    }}>
                      <X style={{ width: 14, height: 14 }} />
                    </button>
                  )}
                </div>

                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  {['all', ...categories].map(cat => {
                    const isActive = activeCategory === cat;
                    const label = cat === 'all' ? 'All' : CATEGORY_LABELS[cat] || cat;
                    const count = cat === 'all' ? templates.length : templates.filter(t => t.category === cat).length;
                    return (
                      <button key={cat} onClick={() => setActiveCategory(cat)} style={{
                        padding: '6px 14px', fontSize: 12.5, fontWeight: 500,
                        borderRadius: 100, cursor: 'pointer', fontFamily: 'inherit',
                        background: isActive ? '#0A0A0A' : '#fff',
                        color: isActive ? '#fff' : '#888',
                        border: isActive ? '1px solid #0A0A0A' : '1px solid #EEEEEE',
                        transition: 'all 0.15s',
                      }}>
                        {label} <span style={{ opacity: 0.5, marginLeft: 2 }}>{count}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {fetchLoading && (
                <div style={{ textAlign: 'center', padding: '80px 0' }}>
                  <Loader2 style={{ width: 20, height: 20, animation: 'spin 1s linear infinite', color: '#CCC' }} />
                </div>
              )}

              {/* Workflow cards */}
              {Object.entries(grouped).map(([category, items]) => (
                <div key={category} style={{ marginBottom: 36 }}>
                  <h3 style={{
                    fontSize: 11, fontWeight: 600, color: '#BBBBBB', letterSpacing: '0.06em',
                    textTransform: 'uppercase', marginBottom: 12, padding: '0 4px',
                  }}>
                    {category}
                  </h3>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10 }}>
                    {items.map(t => (
                      <button key={t.id} className="wf-card" onClick={() => openWorkflow(t)} style={{
                        textAlign: 'left', padding: '20px',
                        background: '#fff', border: '1px solid #F0F0F0',
                        borderRadius: 14, cursor: 'pointer', fontFamily: 'inherit',
                        boxShadow: '0 1px 4px rgba(0,0,0,0.02)',
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                          <span style={{ fontSize: 14, fontWeight: 600, color: '#0A0A0A', letterSpacing: '-0.015em' }}>{t.name}</span>
                          <span style={{
                            fontSize: 10, fontWeight: 500, color: '#CCC',
                            background: '#F8F8F8', padding: '2px 8px', borderRadius: 100,
                          }}>{t.fields?.length || 0} fields</span>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              ))}

              {!fetchLoading && filtered.length === 0 && (
                <div style={{ textAlign: 'center', padding: '60px 0' }}>
                  <p style={{ fontSize: 14, color: '#BBB' }}>No workflows found.</p>
                </div>
              )}
            </>
          )}

          {/* ═══ FORM + RESULT STATE ═══ */}
          {selected && !result && (
            <div style={{ maxWidth: 600, margin: '0 auto', animation: 'slideUp 0.3s ease-out' }}>
              <p style={{ fontSize: 14.5, color: '#888', marginBottom: 28, lineHeight: 1.55 }}>
                Fill in the details below. Spectr will generate a complete, airtight document with proper legal formatting and citations.
              </p>

              {(selected.fields || []).map(field => (
                <div key={field.name} style={{ marginBottom: 18 }}>
                  <label style={{ display: 'block', fontSize: 13, fontWeight: 600, color: '#333', marginBottom: 6 }}>
                    {field.label}
                  </label>
                  {field.type === 'textarea' ? (
                    <textarea
                      value={formData[field.name] || ''}
                      onChange={e => setFormData(prev => ({ ...prev, [field.name]: e.target.value }))}
                      rows={4}
                      style={{
                        width: '100%', padding: '12px 14px', fontSize: 14,
                        border: '1px solid #E8E8E8', borderRadius: 10, resize: 'vertical',
                        outline: 'none', fontFamily: 'inherit', lineHeight: 1.6,
                        boxSizing: 'border-box', transition: 'border-color 0.15s',
                        background: '#FAFAFA',
                      }}
                      onFocus={e => e.target.style.borderColor = '#C0C0C0'}
                      onBlur={e => e.target.style.borderColor = '#E8E8E8'}
                    />
                  ) : (
                    <input
                      type={field.type === 'date' ? 'date' : 'text'}
                      value={formData[field.name] || ''}
                      onChange={e => setFormData(prev => ({ ...prev, [field.name]: e.target.value }))}
                      style={{
                        width: '100%', padding: '10px 14px', fontSize: 14,
                        border: '1px solid #E8E8E8', borderRadius: 10,
                        outline: 'none', fontFamily: 'inherit',
                        boxSizing: 'border-box', transition: 'border-color 0.15s',
                        background: '#FAFAFA',
                      }}
                      onFocus={e => e.target.style.borderColor = '#C0C0C0'}
                      onBlur={e => e.target.style.borderColor = '#E8E8E8'}
                    />
                  )}
                </div>
              ))}

              {error && (
                <div style={{
                  padding: '12px 16px', background: '#FFF5F5', border: '1px solid #FED7D7',
                  borderRadius: 10, fontSize: 13, color: '#C53030', marginBottom: 16,
                }}>
                  {error}
                </div>
              )}

              <button
                onClick={handleGenerate}
                disabled={generating}
                style={{
                  width: '100%', padding: '14px', marginTop: 8,
                  background: '#0A0A0A', color: '#fff', border: 'none',
                  borderRadius: 12, fontSize: 15, fontWeight: 600,
                  cursor: generating ? 'default' : 'pointer',
                  opacity: generating ? 0.5 : 1,
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                  fontFamily: 'inherit', transition: 'opacity 0.15s',
                }}
              >
                {generating ? (
                  <><Loader2 style={{ width: 16, height: 16, animation: 'spin 1s linear infinite' }} /> Generating document...</>
                ) : (
                  'Generate Document'
                )}
              </button>
            </div>
          )}

          {/* ═══ RESULT STATE ═══ */}
          {selected && result && (
            <div style={{ maxWidth: 740, margin: '0 auto', animation: 'fadeIn 0.3s ease-out' }}>
              {/* Export bar */}
              <div style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                marginBottom: 24, padding: '14px 18px',
                background: '#FAFAFA', borderRadius: 12, border: '1px solid #F0F0F0', gap: 10, flexWrap: 'wrap',
              }}>
                <span style={{ fontSize: 13.5, fontWeight: 600, color: '#333' }}>
                  {selected.name}
                </span>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  {/* Primary: Open in Google Docs */}
                  <button
                    onClick={handleOpenInGoogleDocs}
                    disabled={openingInDrive || !result.docx_file_id}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px',
                      background: '#0A0A0A', border: '1px solid #0A0A0A', borderRadius: 8,
                      fontSize: 13, fontWeight: 600, cursor: openingInDrive ? 'default' : 'pointer',
                      fontFamily: 'inherit', color: '#fff',
                      opacity: openingInDrive || !result.docx_file_id ? 0.6 : 1,
                      transition: 'opacity 0.15s',
                    }}
                    title={driveStatus.connected ? 'Upload to Drive and open as Google Doc' : 'Connect Google Drive first'}
                  >
                    {openingInDrive ? (
                      <Loader2 style={{ width: 13, height: 13, animation: 'spin 1s linear infinite' }} />
                    ) : (
                      <ExternalLink style={{ width: 13, height: 13 }} />
                    )}
                    {openingInDrive ? 'Opening in Docs…' : driveStatus.connected ? 'Open in Google Docs' : 'Connect Drive'}
                  </button>
                  <button className="export-btn" onClick={() => handleExport('docx')} disabled={!!exporting} style={{
                    display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px',
                    background: '#fff', border: '1px solid #E8E8E8', borderRadius: 8,
                    fontSize: 13, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit',
                    color: exporting === 'docx' ? '#AAA' : '#333',
                  }}>
                    {exporting === 'docx' ? <Loader2 style={{ width: 13, height: 13, animation: 'spin 1s linear infinite' }} /> : <FileText style={{ width: 13, height: 13 }} />}
                    Word
                  </button>
                  <button className="export-btn" onClick={() => handleExport('pdf')} disabled={!!exporting} style={{
                    display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px',
                    background: '#fff', border: '1px solid #E8E8E8', borderRadius: 8,
                    fontSize: 13, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit',
                    color: exporting === 'pdf' ? '#AAA' : '#333',
                  }}>
                    {exporting === 'pdf' ? <Loader2 style={{ width: 13, height: 13, animation: 'spin 1s linear infinite' }} /> : <FileDown style={{ width: 13, height: 13 }} />}
                    PDF
                  </button>
                </div>
              </div>

              {/* Document content — rendered as a legal document, not a chat response */}
              <div style={{
                background: '#fff', borderRadius: 4,
                border: '1px solid #E5E5E5',
                padding: '56px 64px',
                boxShadow: '0 4px 20px rgba(0,0,0,0.04)',
                fontFamily: "'EB Garamond', 'Times New Roman', Georgia, serif",
                fontSize: 14.5, lineHeight: 1.75, color: '#1A1A1A',
                minHeight: 600,
              }}>
                <ResponseCard
                  responseText={result.response_text}
                  sources={result.sources}
                  onExport={(format) => handleExport(format)}
                />
              </div>

              {/* Actions */}
              <div style={{ display: 'flex', gap: 10, marginTop: 20 }}>
                <button onClick={() => { setResult(null); setError(''); }} style={{
                  flex: 1, padding: '12px', background: '#fff', color: '#333',
                  border: '1px solid #E8E8E8', borderRadius: 10, fontSize: 14, fontWeight: 500,
                  cursor: 'pointer', fontFamily: 'inherit',
                }}>
                  Edit & Regenerate
                </button>
                <button onClick={goBack} style={{
                  flex: 1, padding: '12px', background: '#0A0A0A', color: '#fff',
                  border: 'none', borderRadius: 10, fontSize: 14, fontWeight: 600,
                  cursor: 'pointer', fontFamily: 'inherit',
                }}>
                  New Workflow
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
