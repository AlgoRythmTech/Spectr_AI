import React, { useState, useEffect } from 'react';
import { X, ExternalLink, Copy, Check, Scale } from 'lucide-react';

export default function CitationPanel({ citation, onClose }) {
  const [copied, setCopied] = useState(false);
  const [statuteData, setStatuteData] = useState(null);
  const [loading, setLoading] = useState(false);
  
  useEffect(() => {
    if (citation?.type === 'statute' && citation.is_verified) {
      setLoading(true);
      fetch(`/api/statutes/${encodeURIComponent(citation.act)}/${encodeURIComponent(citation.section)}`)
        .then(res => res.json())
        .then(data => {
          setStatuteData(data);
          setLoading(false);
        })
        .catch(err => {
          console.error(err);
          setLoading(false);
        });
    }
  }, [citation]);

  if (!citation) return null;

  const handleCopy = () => {
    const textToCopy = statuteData?.text || citation.match_text;
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div style={{
      position: 'fixed', top: 0, right: 0, bottom: 0, width: 400,
      background: '#FFF', borderLeft: '1px solid #E5E7EB',
      boxShadow: '-8px 0 24px rgba(0,0,0,0.05)', zIndex: 100,
      display: 'flex', flexDirection: 'column',
      animation: 'slideInRight 0.3s ease-out'
    }}>
      <div style={{
        padding: '16px 20px', borderBottom: '1px solid #E5E7EB',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        background: '#FAFAFA'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Scale style={{ width: 16, height: 16, color: '#000' }} />
          <h3 style={{ fontSize: 14, fontWeight: 700, margin: 0, letterSpacing: '-0.01em' }}>
            Citation Verifier
          </h3>
        </div>
        <button onClick={onClose} style={{ color: '#6B7280', background: 'none', border: 'none', cursor: 'pointer' }}>
          <X style={{ width: 18, height: 18 }} />
        </button>
      </div>

      <div style={{ padding: 24, flex: 1, overflowY: 'auto' }}>
        {citation.type === 'statute' ? (
          <div>
            <div style={{ marginBottom: 20 }}>
              <span style={{ fontSize: 11, fontWeight: 700, color: '#166534', background: '#DCFCE7', padding: '2px 6px', borderRadius: 4, letterSpacing: '0.05em' }}>VERIFIED STATUTE</span>
              <h2 style={{ fontSize: 20, fontWeight: 700, margin: '8px 0 4px', color: '#111827' }}>Section {citation.section}</h2>
              <p style={{ fontSize: 13, color: '#4B5563', margin: 0 }}>{citation.act}</p>
            </div>
            
            {loading ? (
              <div style={{ padding: 20, textAlign: 'center', color: '#6B7280', fontSize: 13 }}>Loading full text...</div>
            ) : statuteData ? (
              <div style={{ background: '#F9FAFB', border: '1px solid #E5E7EB', borderRadius: 8, padding: 16 }}>
                <p style={{ fontSize: 14, lineHeight: 1.7, color: '#1F2937', margin: 0, whiteSpace: 'pre-wrap', fontFamily: "'Charter', serif" }}>
                  {statuteData.text}
                </p>
              </div>
            ) : (
              <div style={{ background: '#F9FAFB', border: '1px solid #E5E7EB', borderRadius: 8, padding: 16 }}>
                <p style={{ fontSize: 14, lineHeight: 1.7, color: '#1F2937', margin: 0, whiteSpace: 'pre-wrap', fontFamily: "'Charter', serif" }}>
                  {citation.text_preview || "Full text not available."}
                </p>
              </div>
            )}
            
            <div style={{ marginTop: 24, display: 'flex', gap: 12 }}>
               <button onClick={handleCopy} style={{ flex: 1, padding: '10px', background: '#000', color: '#FFF', borderRadius: 6, fontSize: 13, fontWeight: 600, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, border: 'none', cursor: 'pointer' }}>
                 {copied ? <Check style={{ width: 14, height: 14 }} /> : <Copy style={{ width: 14, height: 14 }} />}
                 {copied ? "Copied" : "Copy Full Text"}
               </button>
            </div>
          </div>
        ) : (
          <div>
             <div style={{ marginBottom: 20 }}>
              <span style={{ fontSize: 11, fontWeight: 700, color: '#1D4ED8', background: '#DBEAFE', padding: '2px 6px', borderRadius: 4, letterSpacing: '0.05em' }}>INDIANKANOON LINK</span>
              <h2 style={{ fontSize: 18, fontWeight: 700, margin: '8px 0 4px', color: '#111827' }}>{citation.case_name}</h2>
            </div>
            
            <div style={{ background: '#F9FAFB', border: '1px dashed #D1D5DB', borderRadius: 8, padding: 24, textAlign: 'center' }}>
               <p style={{ fontSize: 14, color: '#4B5563', margin: '0 0 16px' }}>View the full judgment on IndianKanoon.</p>
               <a href={citation.link} target="_blank" rel="noreferrer" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '10px 16px', background: '#FFF', border: '1px solid #D1D5DB', borderRadius: 6, color: '#111827', textDecoration: 'none', fontSize: 13, fontWeight: 600 }}>
                 Open Judgment
                 <ExternalLink style={{ width: 14, height: 14 }} />
               </a>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
