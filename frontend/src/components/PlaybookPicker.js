import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { BookOpen, FileText, Search, Check } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const API = process.env.NODE_ENV === 'development' ? '/api' : '/api';

/* Fallback list in case API unavailable */
const FALLBACK_PLAYBOOKS = [
  { id: 'nda',                  title: 'NDA',                      category: 'contracts',   template: 'Draft a Non-Disclosure Agreement between [Party A] and [Party B]...' },
  { id: 'spa',                  title: 'Share Purchase Agreement', category: 'contracts',   template: 'Draft a Share Purchase Agreement for acquisition of...' },
  { id: 'sha',                  title: 'Shareholders Agreement',   category: 'contracts',   template: 'Draft a Shareholders Agreement with tag-along, drag-along, ROFR...' },
  { id: 'jv',                   title: 'Joint Venture',            category: 'contracts',   template: 'Draft a Joint Venture Agreement for...' },
  { id: 'service_agreement',    title: 'Service Agreement',        category: 'contracts',   template: 'Draft a Service Agreement with SLA, indemnity, liability caps...' },
  { id: 'employment_agreement', title: 'Employment Agreement',     category: 'contracts',   template: 'Draft an Employment Agreement with non-compete, non-solicit, IP assignment...' },
  { id: 'lease_agreement',      title: 'Lease Agreement',          category: 'contracts',   template: 'Draft a Lease Agreement for commercial/residential property...' },
  { id: 'franchise_agreement',  title: 'Franchise Agreement',      category: 'contracts',   template: 'Draft a Franchise Agreement with territory, royalty, training clauses...' },
  { id: 'redlining',            title: 'Contract Redline',         category: 'analysis',    template: 'Review and redline the attached contract for risks and non-standard terms...' },
  { id: 'due_diligence',        title: 'Due Diligence',            category: 'analysis',    template: 'Conduct due diligence on [Company] covering corporate, legal, tax, litigation...' },
  { id: 'chronology',           title: 'Case Chronology',          category: 'litigation',  template: 'Build a chronology of events for the matter from these documents...' },
  { id: 'notice_reply',         title: 'Notice Reply',             category: 'litigation',  template: 'Draft a legal reply to the attached notice...' },
];

/**
 * Playbook picker dropdown.
 * Triggered by typing "/" at the start of the input, or clicking a button.
 *
 * Props:
 *   anchor: { x, y } — position to anchor dropdown (or null for default)
 *   searchTerm: string — user-typed filter (after the /)
 *   onSelect: (playbook) => void  — called when user picks one
 *   onClose: () => void
 *   isOpen: bool
 */
export function PlaybookPicker({ isOpen, anchor, searchTerm = '', onSelect, onClose }) {
  const { getToken } = useAuth();
  const [playbooks, setPlaybooks] = useState(FALLBACK_PLAYBOOKS);
  const [highlight, setHighlight] = useState(0);
  const listRef = useRef(null);

  // Fetch from API on open
  useEffect(() => {
    if (!isOpen) return;
    (async () => {
      try {
        let token = '';

        try { token = await getToken() || token; } catch { /**/ }
        try { token = await getToken() || token; } catch {}
        const res = await fetch(`${API}/agent/playbooks`, {
          headers: { 'Authorization': `Bearer ${token}` },
          credentials: 'include',
        });
        if (!res.ok) return;
        const data = await res.json();
        if (data.playbooks?.length) {
          // Merge API data with local templates (API = authoritative for titles, fallback = templates)
          const merged = data.playbooks.map(pb => {
            const fb = FALLBACK_PLAYBOOKS.find(f => f.id === pb.id);
            return { ...pb, template: fb?.template || `Generate a ${pb.title}...` };
          });
          setPlaybooks(merged);
        }
      } catch (e) { /* keep fallback */ }
    })();
  }, [isOpen, getToken]);

  const filtered = searchTerm
    ? playbooks.filter(p =>
        p.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        p.id.includes(searchTerm.toLowerCase()) ||
        p.category?.toLowerCase().includes(searchTerm.toLowerCase())
      )
    : playbooks;

  // Reset highlight when filter changes
  useEffect(() => { setHighlight(0); }, [searchTerm, isOpen]);

  // Keyboard nav
  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e) => {
      if (e.key === 'ArrowDown') { e.preventDefault(); setHighlight(h => Math.min(h + 1, filtered.length - 1)); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); setHighlight(h => Math.max(h - 1, 0)); }
      else if (e.key === 'Enter' && filtered[highlight]) { e.preventDefault(); onSelect?.(filtered[highlight]); }
      else if (e.key === 'Escape') { e.preventDefault(); onClose?.(); }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [isOpen, filtered, highlight, onSelect, onClose]);

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 6, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 6, scale: 0.98 }}
        transition={{ duration: 0.15, ease: [0.16, 1, 0.3, 1] }}
        ref={listRef}
        style={{
          position: 'absolute',
          bottom: anchor?.bottom || '100%',
          left: anchor?.left ?? 0,
          marginBottom: 8,
          width: 340, maxHeight: 360,
          background: '#fff', border: '1px solid rgba(0,0,0,0.08)',
          borderRadius: 14, boxShadow: '0 20px 60px rgba(0,0,0,0.12), 0 0 0 1px rgba(0,0,0,0.04)',
          zIndex: 100, padding: 6, overflow: 'hidden',
          fontFamily: "'Inter', sans-serif",
          display: 'flex', flexDirection: 'column',
        }}>
        <div style={{ padding: '8px 12px 6px', fontSize: 10, fontWeight: 700, color: '#BBB', letterSpacing: '.08em', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: 5 }}>
          <BookOpen style={{ width: 10, height: 10 }} /> Playbooks
        </div>
        <div style={{ overflowY: 'auto', flex: 1 }}>
          {filtered.length === 0 ? (
            <div style={{ padding: 20, textAlign: 'center', fontSize: 12, color: '#BBB' }}>No playbooks match "{searchTerm}"</div>
          ) : (
            filtered.map((pb, i) => (
              <motion.button
                key={pb.id}
                onClick={() => onSelect?.(pb)}
                onMouseEnter={() => setHighlight(i)}
                style={{
                  width: '100%', textAlign: 'left', padding: '9px 12px',
                  background: i === highlight ? 'rgba(10,10,10,0.05)' : 'transparent',
                  border: 'none', borderRadius: 8, display: 'flex', alignItems: 'center', gap: 10,
                  cursor: 'pointer', fontFamily: 'inherit', transition: 'background 0.15s',
                }}>
                <div style={{ width: 28, height: 28, borderRadius: 7, background: i === highlight ? '#0A0A0A' : '#F5F5F5', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, transition: 'all 0.2s' }}>
                  <FileText style={{ width: 12, height: 12, color: i === highlight ? '#fff' : '#888' }} />
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ fontSize: 13, fontWeight: 600, color: '#0A0A0A' }}>{pb.title}</span>
                    <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 4, background: '#F0F0F0', color: '#888', fontFamily: "'JetBrains Mono', monospace", fontWeight: 600 }}>/{pb.id}</span>
                  </div>
                  {pb.category && (
                    <div style={{ fontSize: 10.5, color: '#999', marginTop: 1 }}>{pb.category}</div>
                  )}
                </div>
              </motion.button>
            ))
          )}
        </div>
        <div style={{ padding: '6px 12px', borderTop: '1px solid #F5F5F5', fontSize: 10, color: '#BBB', display: 'flex', gap: 10 }}>
          <span>↑↓ navigate</span>
          <span>⏎ select</span>
          <span>esc close</span>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
