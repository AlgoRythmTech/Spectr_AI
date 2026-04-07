import React, { useState } from 'react';
import './VaultPage.css';

const VaultPage = () => {
  const [files, setFiles] = useState([]);
  const [analysisState, setAnalysisState] = useState('idle'); // idle, uploading, analyzing, done
  const [streamedText, setStreamedText] = useState('');
  const [statusMessage, setStatusMessage] = useState('');

  // Dummy file content extractor (in production, we'd send the actual PDFs to a text extraction endpoint)
  const handleFileUpload = (e) => {
    const uploadedFiles = Array.from(e.target.files);
    
    const newFiles = uploadedFiles.map(file => ({
      id: Math.random().toString(36).substr(2, 9),
      name: file.name,
      size: (file.size / 1024).toFixed(1) + ' KB',
      status: 'Ready',
      // We mock the content parsing for the MVP
      content: `Extracted text from ${file.name}. This document discusses various financial transactions and legal obligations.`
    }));
    
    setFiles([...files, ...newFiles]);
  };

  const removeFile = (id) => {
    setFiles(files.filter(f => f.id !== id));
  };

  const triggerSkill = async (skillType) => {
    if (files.length === 0) {
      alert("Please upload documents to the Vault first.");
      return;
    }
    
    setAnalysisState('analyzing');
    setStreamedText('');
    setStatusMessage('Booting Intelligence Council...');
    
    try {
      const payload = {
        vault_id: "tmp_vault_123",
        documents: files.map(f => ({ filename: f.name, content: f.content })),
        analysis_type: skillType
      };

      const response = await fetch('http://localhost:8000/api/vault/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) throw new Error("Vault API Error");

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      
      let fullText = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        const chunks = decoder.decode(value).split('\n');
        for (const chunk of chunks) {
          if (!chunk) continue;
          try {
            const parsed = JSON.parse(chunk);
            if (parsed.type === 'vault_status') {
              setStatusMessage(parsed.status);
            } else if (parsed.type === 'vault_chunk') {
              fullText += parsed.content;
              setStreamedText(fullText);
            } else if (parsed.type === 'vault_complete') {
              setAnalysisState('done');
            }
          } catch (e) {
            // Unparseable boundary chunk
          }
        }
      }
    } catch (e) {
      console.error(e);
      setAnalysisState('done');
      setStreamedText(`**System Error:** Could not complete Vault analysis. Details: ${e.message}`);
    }
  };

  // Natively render Markdown into UI elements (simulating markdown-it)
  const renderMarkdown = (text) => {
    if (!text) return null;
    
    // Very basic regex-based renderer for the Vault Output MVP
    const lines = text.split('\n');
    let inStrategy = false;
    
    return lines.map((line, i) => {
      // Handle the Jaw-breaking Claude-style reasoning blocks
      if (line.includes('<internal_strategy>')) {
          inStrategy = true;
          return <div key={i} className="md-strategy-header">🧠 Conscious Reasoning Stream Initiated</div>;
      }
      if (line.includes('</internal_strategy>')) {
          inStrategy = false;
          return <div key={i} className="md-strategy-footer">✓ Strategic Synthesis Complete</div>;
      }
      if (inStrategy) {
          return <div key={i} className="md-strategy-line">{line}</div>;
      }

      if (line.startsWith('## ')) return <h2 key={i} className="md-h2">{line.replace('## ', '')}</h2>;
      if (line.startsWith('### ')) return <h3 key={i} className="md-h3">{line.replace('### ', '')}</h3>;
      if (line.startsWith('> ')) return <blockquote key={i} className="md-quote">{line.replace('> ', '')}</blockquote>;
      if (line.startsWith('- ')) return <li key={i} className="md-li">{line.replace('- ', '')}</li>;
      if (line.match(/^\|.*\|$/)) {
          // It's a table row
          const cols = line.split('|').filter(c => c.trim().length > 0);
          if (line.includes('---')) return null; // Skip markdown separator
          return (
              <div key={i} className="md-table-row">
                  {cols.map((c, j) => <div key={j} className="md-table-cell">{c.trim()}</div>)}
              </div>
          );
      }
      return <p key={i} className="md-p" dangerouslySetInnerHTML={{__html: line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')}} />;
    });
  };

  return (
    <div className="vault-container animate-fade-in">
      <header className="vault-header">
        <div>
          <h1 className="vault-title">The Legal Vault</h1>
          <p className="vault-subtitle">Cross-document forensic analysis & timeline generation.</p>
        </div>
      </header>

      <div className="vault-layout">
        
        {/* Left Panel: File Repository */}
        <div className="vault-sidebar">
          <div className="sidebar-section">
            <h3 className="section-label">Data Room</h3>
            <label className="upload-dropzone">
              <input type="file" multiple onChange={handleFileUpload} style={{display: 'none'}} accept=".pdf,.docx,.txt" />
              <div className="dropzone-content">
                <span className="dropzone-icon">📥</span>
                <span className="dropzone-text">Drop Exhibits Here</span>
                <span className="dropzone-sub">PDF, DOCX, TXT</span>
              </div>
            </label>
            
            <div className="file-list">
              {files.map(file => (
                <div key={file.id} className="file-item">
                  <div className="file-icon">📄</div>
                  <div className="file-meta">
                    <span className="file-name">{file.name}</span>
                    <span className="file-size">{file.size}</span>
                  </div>
                  <button className="del-btn" onClick={() => removeFile(file.id)}>×</button>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Panel: AI Skill OS & Output */}
        <div className="vault-main">
          
          {analysisState === 'idle' && (
            <div className="skill-os">
              <h2 className="os-title">Select Intelligence Skill</h2>
              <p className="os-desc">Choose a forensic workflow to execute across all {files.length} uploaded documents.</p>
              
              <div className="skill-grid">
                <div className="skill-card bg-purple" onClick={() => triggerSkill('night_before')}>
                  <div className="skill-icon">💼</div>
                  <h3>The "Night Before" Digest</h3>
                  <p>Instantly summarize the dispute, the fatal errors, and generate the 3-minute oral argument script.</p>
                </div>
                
                <div className="skill-card bg-blue" onClick={() => triggerSkill('timeline')}>
                  <div className="skill-icon">⏱️</div>
                  <h3>Chronological Timeline</h3>
                  <p>Extract every date across all documents and construct a master sequential timeline.</p>
                </div>

                <div className="skill-card bg-red" onClick={() => triggerSkill('contradictions')}>
                  <div className="skill-icon">🔍</div>
                  <h3>Cross-Examination Matrix</h3>
                  <p>Aggressively hunt for discrepancies, conflicting dates, and opposing counsel contradictions.</p>
                </div>
              </div>
            </div>
          )}

          {(analysisState === 'analyzing' || analysisState === 'done') && (
            <div className="vault-output-panel">
              {analysisState === 'analyzing' && (
                <div className="vault-loading-bar">
                  <div className="vault-spinner"></div>
                  <span>{statusMessage}</span>
                </div>
              )}
              
              <div className="vault-document-canvas">
                {renderMarkdown(streamedText)}
              </div>
              
              {analysisState === 'done' && (
                 <button className="reset-btn" onClick={() => setAnalysisState('idle')}>← Run Another Skill</button>
              )}
            </div>
          )}
          
        </div>
      </div>
    </div>
  );
};

export default VaultPage;
