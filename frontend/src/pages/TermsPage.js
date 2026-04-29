import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { FileText, Download, ArrowLeft, ShieldCheck } from 'lucide-react';

/**
 * /terms — the page the T&C link in the acceptance modal opens to.
 * Shows "click here to download the T&C" which downloads the actual PDF
 * we stored at /public/spectr-terms.pdf.
 */
export default function TermsPage() {
  const navigate = useNavigate();
  const [fileSizeKB, setFileSizeKB] = useState(null);

  useEffect(() => {
    // Fetch the PDF's HEAD to display the file size — confirms the file is live
    fetch('/spectr-terms.pdf', { method: 'HEAD' })
      .then(r => {
        const size = r.headers.get('content-length');
        if (size) setFileSizeKB(Math.round(parseInt(size, 10) / 1024));
      })
      .catch(() => { /* ignore */ });
  }, []);

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(180deg, #FAFAFA 0%, #F4F4F5 100%)',
      fontFamily: "'Inter', sans-serif",
      color: '#0A0A0A',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: '60px 24px',
    }}>
      <motion.div
        initial={{ opacity: 0, y: 18, filter: 'blur(10px)' }}
        animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
        transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
        style={{
          maxWidth: 560, width: '100%',
          background: '#fff',
          border: '1px solid rgba(0,0,0,0.06)',
          borderRadius: 20,
          boxShadow: '0 20px 60px rgba(0,0,0,0.08), 0 4px 16px rgba(0,0,0,0.04)',
          padding: '44px 44px 36px',
          textAlign: 'center',
        }}
      >
        {/* Icon */}
        <div style={{
          width: 56, height: 56, borderRadius: 14,
          background: 'linear-gradient(135deg, #0A0A0A, #1F1F1F)',
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
          marginBottom: 22, boxShadow: '0 8px 24px rgba(0,0,0,0.15)',
        }}>
          <FileText style={{ width: 24, height: 24, color: '#fff', strokeWidth: 1.7 }} />
        </div>

        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 6,
          padding: '5px 12px', marginBottom: 14,
          background: 'rgba(10,10,10,0.04)', borderRadius: 999,
          fontSize: 11, fontWeight: 500, color: '#555',
          letterSpacing: '0.2em', textTransform: 'uppercase',
        }}>
          <ShieldCheck style={{ width: 11, height: 11 }} />
          Legal Document
        </div>

        <h1 style={{
          fontSize: 32, fontWeight: 500, letterSpacing: '-0.045em',
          lineHeight: 1.1, margin: 0,
          background: 'linear-gradient(to bottom right, #0A0A0A 40%, rgba(10,10,10,0.5))',
          WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text',
        }}>
          Spectr — Terms &amp; Conditions
        </h1>
        <p style={{
          marginTop: 12, fontSize: 14, color: '#6B7280',
          letterSpacing: '-0.005em', lineHeight: 1.6, maxWidth: 420, marginLeft: 'auto', marginRight: 'auto',
        }}>
          This is the full agreement governing your use of Spectr — the AI Legal &amp; Accounting Platform. Click below to download the PDF.
        </p>

        {/* Primary download button */}
        <a
          href="/spectr-terms.pdf"
          download="Spectr-Terms-and-Conditions.pdf"
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 10,
            padding: '14px 28px',
            marginTop: 28,
            background: '#0A0A0A', color: '#fff',
            fontFamily: "'Inter', sans-serif",
            fontSize: 14, fontWeight: 500, letterSpacing: '-0.01em',
            textDecoration: 'none', borderRadius: 12,
            boxShadow: '0 8px 24px rgba(10,10,10,0.2), inset 0 1px 0 rgba(255,255,255,0.1)',
            transition: 'all 0.2s cubic-bezier(0.16,1,0.3,1)',
          }}
          onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = '0 14px 36px rgba(10,10,10,0.3), inset 0 1px 0 rgba(255,255,255,0.12)'; }}
          onMouseLeave={e => { e.currentTarget.style.transform = 'none'; e.currentTarget.style.boxShadow = '0 8px 24px rgba(10,10,10,0.2), inset 0 1px 0 rgba(255,255,255,0.1)'; }}
        >
          <Download style={{ width: 15, height: 15, strokeWidth: 2 }} />
          Click here to download the T&amp;C
        </a>

        {/* View inline option */}
        <div style={{ marginTop: 14 }}>
          <a
            href="/spectr-terms.pdf"
            target="_blank"
            rel="noreferrer noopener"
            style={{
              fontSize: 12.5, color: '#6B7280', fontWeight: 500,
              textDecoration: 'underline', textDecorationColor: 'rgba(0,0,0,0.18)',
              textUnderlineOffset: 3,
            }}
          >
            Or open in a new tab
          </a>
          {fileSizeKB != null && (
            <span style={{ fontSize: 11.5, color: '#9CA3AF', marginLeft: 10 }}>· PDF · {fileSizeKB} KB</span>
          )}
        </div>

        {/* Divider */}
        <div style={{ height: 1, background: 'rgba(0,0,0,0.05)', margin: '30px 0 22px' }} />

        {/* Back link */}
        <button
          onClick={() => (window.history.length > 1 ? window.history.back() : navigate('/'))}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 6,
            background: 'none', border: 'none',
            fontFamily: "'Inter', sans-serif", fontSize: 13,
            color: '#6B7280', cursor: 'pointer',
            letterSpacing: '-0.005em',
          }}
          onMouseEnter={e => (e.currentTarget.style.color = '#0A0A0A')}
          onMouseLeave={e => (e.currentTarget.style.color = '#6B7280')}
        >
          <ArrowLeft style={{ width: 13, height: 13 }} /> Back
        </button>
      </motion.div>
    </div>
  );
}
