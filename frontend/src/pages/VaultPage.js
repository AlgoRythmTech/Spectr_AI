import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import ResponseCard from '../components/ResponseCard';
import {
  Upload, FileText, File, Image, X, Loader2, Search,
  AlertTriangle, CheckCircle, Clock, BarChart3, Shield, FolderOpen
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const DOC_TYPE_LABELS = {
  contract: 'Contract / Agreement',
  court_order: 'Court Order / Judgment',
  gst_notice: 'GST Notice / SCN',
  it_notice: 'Income Tax Notice',
  financial_statement: 'Financial Statement',
  corporate_document: 'Corporate Document',
  property_document: 'Property Document',
  other: 'Other',
};

const ANALYSIS_TYPES = [
  { id: 'general', label: 'General Analysis', icon: Search },
  { id: 'anomaly', label: 'Anomaly Detection', icon: AlertTriangle },
  { id: 'contract_risk', label: 'Contract Risk Scan', icon: Shield },
  { id: 'timeline', label: 'Timeline & Deadlines', icon: Clock },
  { id: 'obligations', label: 'Obligation Tracker', icon: CheckCircle },
  { id: 'response', label: 'Draft Response', icon: FileText },
];

export default function VaultPage() {
  const { user } = useAuth();
  const [documents, setDocuments] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [bulkQuestion, setBulkQuestion] = useState('');
  const [bulkAnswer, setBulkAnswer] = useState(null);
  const [selectedDocs, setSelectedDocs] = useState([]);

  useEffect(() => { fetchDocuments(); }, []);

  const fetchDocuments = async () => {
    try {
      const res = await fetch(`${API}/vault/documents`, { credentials: 'include' });
      if (res.ok) setDocuments(await res.json());
    } catch {}
  };

  const handleUpload = async (files) => {
    setUploading(true);
    for (const file of files) {
      const formData = new FormData();
      formData.append('file', file);
      try {
        const res = await fetch(`${API}/vault/upload`, {
          method: 'POST',
          credentials: 'include',
          body: formData,
        });
        if (res.ok) {
          const doc = await res.json();
          setDocuments(prev => [doc, ...prev]);
        }
      } catch (err) {
        console.error('Upload error:', err);
      }
    }
    setUploading(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files.length) handleUpload(Array.from(e.dataTransfer.files));
  };

  const handleAnalyze = async (docId, analysisType) => {
    setAnalyzing(true);
    setAnalysis(null);
    try {
      const res = await fetch(`${API}/vault/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ document_id: docId, analysis_type: analysisType }),
      });
      if (res.ok) setAnalysis(await res.json());
    } catch {}
    setAnalyzing(false);
  };

  const handleBulkAsk = async () => {
    if (!bulkQuestion.trim() || selectedDocs.length === 0) return;
    setAnalyzing(true);
    setBulkAnswer(null);
    try {
      const res = await fetch(`${API}/vault/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ question: bulkQuestion, doc_ids: selectedDocs }),
      });
      if (res.ok) setBulkAnswer(await res.json());
    } catch {}
    setAnalyzing(false);
  };

  const getFileIcon = (ext) => {
    if (['pdf'].includes(ext)) return <FileText className="w-4 h-4 text-[#991B1B]" />;
    if (['doc', 'docx'].includes(ext)) return <FileText className="w-4 h-4 text-[#1A1A2E]" />;
    if (['xlsx', 'xls'].includes(ext)) return <BarChart3 className="w-4 h-4 text-[#166534]" />;
    if (['jpg', 'jpeg', 'png'].includes(ext)) return <Image className="w-4 h-4 text-[#B45309]" />;
    return <File className="w-4 h-4 text-[#64748B]" />;
  };

  return (
    <div className="flex flex-col h-full" data-testid="vault-page">
      {/* Top Bar */}
      <div className="h-14 border-b border-[#E2E8F0] px-6 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <FolderOpen className="w-4 h-4 text-[#64748B]" />
          <h1 className="text-base font-semibold text-[#1A1A2E]">Document Vault</h1>
          <span className="text-xs text-[#64748B] font-mono ml-2">{documents.length} documents</span>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Left: Document List */}
        <div className="w-[340px] border-r border-[#E2E8F0] flex flex-col shrink-0">
          {/* Upload Zone */}
          <div
            className={`m-3 border-2 border-dashed rounded-sm p-4 text-center transition-colors cursor-pointer ${
              dragOver ? 'border-[#1A1A2E] bg-[#F8FAFC]' : 'border-[#E2E8F0] hover:border-[#CBD5E1]'
            }`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => document.getElementById('file-upload').click()}
            data-testid="upload-zone"
          >
            {uploading ? (
              <Loader2 className="w-5 h-5 text-[#1A1A2E] animate-spin mx-auto" />
            ) : (
              <Upload className="w-5 h-5 text-[#64748B] mx-auto mb-1" />
            )}
            <p className="text-xs text-[#4A4A4A] font-medium mt-1">
              {uploading ? 'Uploading...' : 'Drop files or click to upload'}
            </p>
            <p className="text-[10px] text-[#94A3B8] mt-0.5">PDF, DOCX, XLSX, Images</p>
            <input
              id="file-upload"
              type="file"
              multiple
              className="hidden"
              onChange={(e) => handleUpload(Array.from(e.target.files))}
              accept=".pdf,.docx,.doc,.xlsx,.xls,.jpg,.jpeg,.png,.txt,.csv"
            />
          </div>

          {/* Bulk Q&A */}
          {documents.length > 0 && (
            <div className="px-3 pb-2">
              <div className="flex items-center gap-2 mb-1">
                <input
                  type="text"
                  value={bulkQuestion}
                  onChange={(e) => setBulkQuestion(e.target.value)}
                  placeholder="Ask across all selected docs..."
                  className="flex-1 text-xs border border-[#E2E8F0] rounded-sm px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-[#0D0D0D]"
                  data-testid="bulk-question-input"
                />
                <button
                  onClick={handleBulkAsk}
                  disabled={!bulkQuestion.trim() || selectedDocs.length === 0}
                  className="text-xs bg-[#1A1A2E] text-white px-2 py-1.5 rounded-sm disabled:opacity-40"
                  data-testid="bulk-ask-btn"
                >
                  Ask
                </button>
              </div>
              <p className="text-[10px] text-[#94A3B8]">{selectedDocs.length} docs selected</p>
            </div>
          )}

          {/* Document List */}
          <div className="flex-1 overflow-y-auto px-3 pb-3 space-y-1">
            {documents.map((doc) => (
              <div
                key={doc.doc_id}
                className={`flex items-start gap-3 p-3 rounded-sm cursor-pointer transition-colors border ${
                  selectedDoc?.doc_id === doc.doc_id
                    ? 'border-[#1A1A2E] bg-[#F8FAFC]'
                    : 'border-transparent hover:bg-[#F8FAFC]'
                }`}
                onClick={() => { setSelectedDoc(doc); setAnalysis(null); }}
                data-testid={`doc-item-${doc.doc_id}`}
              >
                <input
                  type="checkbox"
                  checked={selectedDocs.includes(doc.doc_id)}
                  onChange={(e) => {
                    e.stopPropagation();
                    setSelectedDocs(prev =>
                      prev.includes(doc.doc_id) ? prev.filter(id => id !== doc.doc_id) : [...prev, doc.doc_id]
                    );
                  }}
                  className="mt-1 shrink-0"
                />
                {getFileIcon(doc.file_ext)}
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-[#0D0D0D] truncate">{doc.filename}</p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-[10px] text-[#64748B] font-mono">{DOC_TYPE_LABELS[doc.doc_type] || doc.doc_type}</span>
                    <span className="text-[10px] text-[#94A3B8]">{(doc.size / 1024).toFixed(0)} KB</span>
                  </div>
                </div>
              </div>
            ))}
            {documents.length === 0 && (
              <p className="text-sm text-[#94A3B8] text-center py-8">No documents yet. Upload to begin.</p>
            )}
          </div>
        </div>

        {/* Right: Analysis Area */}
        <div className="flex-1 overflow-y-auto p-6">
          {selectedDoc ? (
            <div>
              <div className="mb-6">
                <h2 className="text-lg font-semibold text-[#0D0D0D] mb-1">{selectedDoc.filename}</h2>
                <p className="text-xs text-[#64748B] font-mono">
                  {DOC_TYPE_LABELS[selectedDoc.doc_type]} | {(selectedDoc.size / 1024).toFixed(0)} KB | Uploaded {new Date(selectedDoc.created_at).toLocaleDateString()}
                </p>
              </div>

              {/* Analysis Buttons */}
              <div className="grid grid-cols-3 gap-2 mb-6">
                {ANALYSIS_TYPES.map((at) => (
                  <button
                    key={at.id}
                    onClick={() => handleAnalyze(selectedDoc.doc_id, at.id)}
                    disabled={analyzing}
                    className="flex items-center gap-2 p-3 border border-[#E2E8F0] rounded-sm text-sm text-[#4A4A4A] hover:bg-[#F8FAFC] hover:border-[#CBD5E1] transition-colors disabled:opacity-40"
                    data-testid={`analyze-${at.id}-btn`}
                  >
                    <at.icon className="w-4 h-4" />
                    {at.label}
                  </button>
                ))}
              </div>

              {/* Analysis Results */}
              {analyzing && (
                <div className="border border-[#E2E8F0] rounded-sm p-6">
                  <div className="flex items-center gap-3">
                    <Loader2 className="w-4 h-4 text-[#1A1A2E] animate-spin" />
                    <span className="text-xs font-semibold tracking-wider text-[#64748B] uppercase">
                      Analyzing document...
                    </span>
                  </div>
                  <div className="space-y-2 mt-4">
                    <div className="h-3 bg-[#F1F5F9] rounded-sm w-full animate-pulse" />
                    <div className="h-3 bg-[#F1F5F9] rounded-sm w-4/5 animate-pulse" />
                  </div>
                </div>
              )}

              {analysis && !analyzing && (
                <ResponseCard
                  sections={analysis.sections}
                  sources={{}}
                  onExport={(format) => {
                    const exportUrl = format === 'docx' ? `${API}/export/word` : `${API}/export/pdf`;
                    fetch(exportUrl, {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      credentials: 'include',
                      body: JSON.stringify({
                        content: analysis.response_text,
                        title: `Analysis - ${selectedDoc.filename}`,
                        format,
                      }),
                    }).then(r => r.blob()).then(blob => {
                      const url = window.URL.createObjectURL(blob);
                      const a = document.createElement('a');
                      a.href = url;
                      a.download = `analysis_${selectedDoc.filename}.${format}`;
                      a.click();
                    });
                  }}
                />
              )}
            </div>
          ) : bulkAnswer ? (
            <ResponseCard sections={bulkAnswer.sections} sources={{}} />
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <FolderOpen className="w-8 h-8 text-[#CBD5E1] mx-auto mb-3" />
                <p className="text-sm text-[#94A3B8]">Select a document to analyze</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
