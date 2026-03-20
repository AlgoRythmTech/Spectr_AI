import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import ResponseCard from '../components/ResponseCard';
import {
  Workflow, Scale, Calculator, ChevronRight, Loader2, ArrowLeft, FileText
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function WorkflowsPage() {
  const { user } = useAuth();
  const [workflows, setWorkflows] = useState([]);
  const [selectedWorkflow, setSelectedWorkflow] = useState(null);
  const [formValues, setFormValues] = useState({});
  const [mode, setMode] = useState('partner');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [tab, setTab] = useState('all');

  useEffect(() => { fetchWorkflows(); }, []);

  const fetchWorkflows = async () => {
    try {
      const res = await fetch(`${API}/workflows`, { credentials: 'include' });
      if (res.ok) setWorkflows(await res.json());
    } catch {}
  };

  const handleGenerate = async () => {
    if (!selectedWorkflow) return;
    setLoading(true);
    setResult(null);
    try {
      const res = await fetch(`${API}/workflows/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          workflow_type: selectedWorkflow.id,
          fields: formValues,
          mode,
        }),
      });
      if (res.ok) setResult(await res.json());
    } catch {}
    setLoading(false);
  };

  const handleExport = async (format) => {
    if (!result) return;
    const endpoint = format === 'docx' ? 'export/word' : 'export/pdf';
    try {
      const res = await fetch(`${API}/${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          content: result.response_text,
          title: result.workflow_name || 'Workflow Document',
          format,
        }),
      });
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${(result.workflow_name || 'document').replace(/\s+/g, '_')}.${format === 'docx' ? 'docx' : 'pdf'}`;
      a.click();
    } catch {}
  };

  const filtered = tab === 'all' ? workflows : workflows.filter(w => w.category === tab);

  if (selectedWorkflow) {
    return (
      <div className="flex flex-col h-full" data-testid="workflow-form-page">
        <div className="h-14 border-b border-[#E2E8F0] px-6 flex items-center gap-4 shrink-0">
          <button
            onClick={() => { setSelectedWorkflow(null); setResult(null); setFormValues({}); }}
            className="flex items-center gap-1 text-sm text-[#4A4A4A] hover:text-[#0D0D0D] transition-colors"
            data-testid="back-to-workflows"
          >
            <ArrowLeft className="w-4 h-4" /> Back
          </button>
          <div className="h-4 w-px bg-[#E2E8F0]" />
          <h1 className="text-sm font-semibold text-[#1A1A2E]">{selectedWorkflow.name}</h1>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-4xl mx-auto flex gap-8">
            {/* Form */}
            <div className="w-[380px] shrink-0">
              <div className="space-y-4">
                {selectedWorkflow.fields?.map((field) => (
                  <div key={field.name}>
                    <label className="text-xs font-semibold text-[#4A4A4A] uppercase tracking-wider mb-1.5 block">
                      {field.label}
                    </label>
                    {field.type === 'textarea' ? (
                      <textarea
                        value={formValues[field.name] || ''}
                        onChange={(e) => setFormValues(prev => ({ ...prev, [field.name]: e.target.value }))}
                        className="w-full border border-[#E2E8F0] rounded-sm px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[#0D0D0D] min-h-[80px] resize-y"
                        data-testid={`field-${field.name}`}
                      />
                    ) : (
                      <input
                        type={field.type === 'date' ? 'date' : 'text'}
                        value={formValues[field.name] || ''}
                        onChange={(e) => setFormValues(prev => ({ ...prev, [field.name]: e.target.value }))}
                        className="w-full border border-[#E2E8F0] rounded-sm px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[#0D0D0D]"
                        data-testid={`field-${field.name}`}
                      />
                    )}
                  </div>
                ))}

                {/* Mode Toggle */}
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setMode('partner')}
                    className={`flex-1 py-2 text-xs font-medium rounded-sm border transition-colors ${
                      mode === 'partner' ? 'bg-[#1A1A2E] text-white border-[#1A1A2E]' : 'border-[#E2E8F0] text-[#4A4A4A]'
                    }`}
                    data-testid="mode-partner-btn"
                  >
                    Partner Mode
                  </button>
                  <button
                    onClick={() => setMode('everyday')}
                    className={`flex-1 py-2 text-xs font-medium rounded-sm border transition-colors ${
                      mode === 'everyday' ? 'bg-[#166534] text-white border-[#166534]' : 'border-[#E2E8F0] text-[#4A4A4A]'
                    }`}
                    data-testid="mode-everyday-btn"
                  >
                    Everyday Mode
                  </button>
                </div>

                <button
                  onClick={handleGenerate}
                  disabled={loading}
                  className="w-full bg-[#1A1A2E] text-white font-medium py-2.5 rounded-sm hover:bg-[#0D0D0D] transition-colors disabled:opacity-40 flex items-center justify-center gap-2 text-sm"
                  data-testid="generate-btn"
                >
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileText className="w-4 h-4" />}
                  {loading ? 'Generating...' : 'Generate Document'}
                </button>
              </div>
            </div>

            {/* Result */}
            <div className="flex-1 min-w-0">
              {loading && (
                <div className="border border-[#E2E8F0] rounded-sm p-6">
                  <div className="flex items-center gap-3">
                    <Loader2 className="w-4 h-4 text-[#1A1A2E] animate-spin" />
                    <span className="text-xs font-semibold tracking-wider text-[#64748B] uppercase">Generating court-ready document...</span>
                  </div>
                  <div className="space-y-2 mt-4">
                    <div className="h-3 bg-[#F1F5F9] rounded-sm w-full animate-pulse" />
                    <div className="h-3 bg-[#F1F5F9] rounded-sm w-4/5 animate-pulse" />
                    <div className="h-3 bg-[#F1F5F9] rounded-sm w-3/5 animate-pulse" />
                  </div>
                </div>
              )}
              {result && !loading && (
                <div>
                  <div className="mb-4 flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-[#0D0D0D]">{result.workflow_name}</h3>
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleExport('docx')}
                        className="text-xs font-medium text-[#4A4A4A] px-3 py-1.5 border border-[#E2E8F0] rounded-sm hover:bg-[#F8FAFC]"
                        data-testid="export-word-workflow"
                      >
                        Export Word
                      </button>
                      <button
                        onClick={() => handleExport('pdf')}
                        className="text-xs font-medium text-[#4A4A4A] px-3 py-1.5 border border-[#E2E8F0] rounded-sm hover:bg-[#F8FAFC]"
                        data-testid="export-pdf-workflow"
                      >
                        Export PDF
                      </button>
                    </div>
                  </div>
                  <div className="border border-[#E2E8F0] rounded-sm p-6 bg-white">
                    <div className="prose prose-sm max-w-none whitespace-pre-wrap text-[15px] leading-7 text-[#0D0D0D]">
                      {result.response_text}
                    </div>
                  </div>
                </div>
              )}
              {!result && !loading && (
                <div className="flex items-center justify-center h-64">
                  <div className="text-center">
                    <FileText className="w-8 h-8 text-[#CBD5E1] mx-auto mb-3" />
                    <p className="text-sm text-[#94A3B8]">Fill in the fields and click Generate</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full" data-testid="workflows-page">
      <div className="h-14 border-b border-[#E2E8F0] px-6 flex items-center gap-4 shrink-0">
        <Workflow className="w-4 h-4 text-[#64748B]" />
        <h1 className="text-base font-semibold text-[#1A1A2E]">Workflows</h1>
        <div className="flex items-center gap-1 ml-4">
          {[
            { id: 'all', label: 'All' },
            { id: 'litigation', label: 'Litigation' },
            { id: 'taxation', label: 'Taxation & Compliance' },
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`px-3 py-1 text-xs font-medium rounded-sm transition-colors ${
                tab === t.id ? 'bg-[#1A1A2E] text-white' : 'text-[#4A4A4A] hover:bg-[#F8FAFC]'
              }`}
              data-testid={`tab-${t.id}`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-5xl mx-auto grid md:grid-cols-2 gap-3">
          {filtered.map((wf) => (
            <button
              key={wf.id}
              onClick={() => setSelectedWorkflow(wf)}
              className="text-left border border-[#E2E8F0] rounded-sm p-4 hover:border-[#CBD5E1] hover:bg-[#F8FAFC] transition-colors group"
              data-testid={`workflow-card-${wf.id}`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3">
                  {wf.category === 'litigation' ? (
                    <Scale className="w-4 h-4 text-[#1A1A2E] mt-0.5" />
                  ) : (
                    <Calculator className="w-4 h-4 text-[#B45309] mt-0.5" />
                  )}
                  <div>
                    <h3 className="text-sm font-medium text-[#0D0D0D] group-hover:text-[#1A1A2E]">{wf.name}</h3>
                    <p className="text-[10px] text-[#64748B] mt-0.5 font-mono">
                      {wf.fields?.length || 0} fields | {wf.category}
                    </p>
                  </div>
                </div>
                <ChevronRight className="w-4 h-4 text-[#CBD5E1] group-hover:text-[#1A1A2E] transition-colors" />
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
