import React, { useEffect, useState, useCallback, useMemo } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Search, Plus, MessageSquare, Scale, Calculator, FileText, Clock, Menu } from 'lucide-react';
import Skeleton from './Skeleton';

const API = process.env.NODE_ENV === 'development' ? '/api' : '/api';

/**
 * PreviousChatsSidebar — left-rail conversation history.
 *
 * Fetches from /api/history and groups by date (Today / Yesterday / This Week / Earlier).
 * Each row opens the historical conversation inline in the Assistant page by
 * emitting a custom window event `spectr:load-history` that AssistantPage listens for.
 */

function sectionForDate(ts) {
  const d = new Date(ts);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 86400000);
  const weekAgo = new Date(today.getTime() - 7 * 86400000);
  if (d >= today) return 'Today';
  if (d >= yesterday) return 'Yesterday';
  if (d >= weekAgo) return 'This week';
  if (d.getFullYear() === now.getFullYear()) return d.toLocaleString('en-US', { month: 'long' });
  return `${d.getFullYear()}`;
}

function iconForTypes(types) {
  if (types?.includes('financial')) return Calculator;
  if (types?.includes('legal')) return Scale;
  return MessageSquare;
}

export default function PreviousChatsSidebar({ collapsed = false, onToggle }) {
  const { getToken, user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [selectedId, setSelectedId] = useState(null);

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    try {
      let token;
      try { token = await getToken(); } catch { token = null; }
      const headers = token ? { 'Authorization': `Bearer ${token}` } : {};

      // Primary: Claude-style threads (auto-titled, persistent). Falls back
      // to legacy /history if the user has no threads yet or the endpoint
      // 404s (e.g. very old backend).
      let threads = null;
      try {
        const r1 = await fetch(`${API}/threads`, { credentials: 'include', headers });
        if (r1.ok) {
          const raw = await r1.json();
          threads = Array.isArray(raw) ? raw : (raw.items || []);
        }
      } catch { /* fall through */ }

      if (threads && threads.length > 0) {
        // Map thread row to the shape this sidebar expects.
        // Thread has: thread_id, title, last_preview, updated_at, message_count, matter_id
        const mapped = threads.map(t => ({
          history_id: t.thread_id,
          thread_id: t.thread_id,
          query: t.title || '(Untitled)',
          mode: 'partner',
          citations_count: null,
          created_at: t.updated_at || t.created_at,
          response_text: t.last_preview || '',
          query_types: ['thread'],
          _is_thread: true,
        }));
        setItems(mapped);
      } else {
        // Legacy fallback: per-query rows (pre-threading)
        const res = await fetch(`${API}/history`, { credentials: 'include', headers });
        if (res.ok) {
          const data = await res.json();
          setItems(Array.isArray(data) ? data : (data.items || []));
        }
      }
    } catch { /* ignore */ }
    setLoading(false);
  }, [getToken]);

  useEffect(() => { fetchHistory(); }, [fetchHistory]);

  // Refresh when we return to /app/assistant (new threads land here)
  useEffect(() => {
    if (location.pathname === '/app/assistant') fetchHistory();
  }, [location.pathname, fetchHistory]);

  // AssistantPage fires this on the first SSE event of a new thread — we
  // want the sidebar to pick it up immediately, with a short delay so the
  // backend has time to persist the row (and the LLM title job to finish
  // is a bonus — if it hasn't, we'll pick up the smart title on the NEXT
  // refresh instead).
  useEffect(() => {
    const onThreadCreated = () => {
      // First refresh: pick up quick-title immediately
      fetchHistory();
      // Second refresh a few seconds later: catch the LLM smart-title swap
      setTimeout(() => fetchHistory(), 4000);
    };
    window.addEventListener('spectr:thread-created', onThreadCreated);
    return () => window.removeEventListener('spectr:thread-created', onThreadCreated);
  }, [fetchHistory]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return items
      .filter(it => !q || (it.query || '').toLowerCase().includes(q))
      .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  }, [items, query]);

  const grouped = useMemo(() => {
    const map = {};
    for (const it of filtered) {
      const sec = sectionForDate(it.created_at);
      if (!map[sec]) map[sec] = [];
      map[sec].push(it);
    }
    return map;
  }, [filtered]);

  const ORDER = ['Today', 'Yesterday', 'This week'];
  const sections = [
    ...ORDER.filter(s => grouped[s]?.length),
    ...Object.keys(grouped).filter(s => !ORDER.includes(s)).sort((a, b) => b.localeCompare(a)),
  ];

  const handleOpen = async (item) => {
    setSelectedId(item.history_id);
    // If this is a thread (new model), fetch the full message list before
    // broadcasting so AssistantPage can rehydrate with ALL turns, not just
    // the first query. Legacy history items (no _is_thread) already have
    // their full payload embedded.
    let detail = item;
    if (item._is_thread && item.thread_id) {
      try {
        let token;
        try { token = await getToken(); } catch { token = null; }
        const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
        const r = await fetch(`${API}/threads/${encodeURIComponent(item.thread_id)}`,
          { credentials: 'include', headers });
        if (r.ok) {
          const full = await r.json();
          detail = { ...item, ...full, _is_thread: true };
        }
      } catch { /* fall through with just item */ }
    }
    window.dispatchEvent(new CustomEvent('spectr:load-history', { detail }));
    if (location.pathname !== '/app/assistant') navigate('/app/assistant');
  };

  const handleNew = () => {
    setSelectedId(null);
    window.dispatchEvent(new CustomEvent('spectr:new-thread'));
    if (location.pathname !== '/app/assistant') navigate('/app/assistant');
  };

  return (
    <aside style={{
      order: 0,
      width: collapsed ? 56 : 272,
      flexShrink: 0,
      height: '100%', display: 'flex', flexDirection: 'column',
      position: 'relative',
      // Apple liquid-glass finish: translucent cream tint, thick blur, inset highlight, faint edge glow
      background: 'linear-gradient(180deg, rgba(255,255,255,0.72) 0%, rgba(250,250,250,0.62) 100%)',
      backdropFilter: 'blur(40px) saturate(180%)',
      WebkitBackdropFilter: 'blur(40px) saturate(180%)',
      borderRight: '1px solid rgba(255,255,255,0.6)',
      boxShadow: 'inset -1px 0 0 rgba(0,0,0,0.04), inset 1px 0 0 rgba(255,255,255,0.8), 4px 0 24px -12px rgba(0,0,0,0.08)',
      fontFamily: "'Inter', sans-serif",
      overflow: 'hidden',
      transition: 'width 0.28s cubic-bezier(0.22, 1, 0.36, 1)',
    }}>
      <style>{`
        .pc-scroll::-webkit-scrollbar { width: 3px; }
        .pc-scroll::-webkit-scrollbar-track { background: transparent; }
        .pc-scroll::-webkit-scrollbar-thumb { background: #E5E5E5; border-radius: 3px; }
        .pc-scroll::-webkit-scrollbar-thumb:hover { background: #CCC; }
        .pc-item { transition: background 0.12s, padding 0.15s; }
        .pc-item:hover { background: rgba(0,0,0,0.035); }
        .pc-item.active { background: #FFFFFF !important; box-shadow: 0 1px 2px rgba(0,0,0,0.04), 0 0 0 1px rgba(0,0,0,0.04); }
      `}</style>

      {/* Collapsed mode — hamburger at top, icons below */}
      {collapsed && (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6, padding: '18px 6px 14px', flex: 1, overflow: 'hidden' }}>
          {onToggle && (
            <button
              onClick={onToggle}
              title="Expand chats"
              aria-label="Expand chats"
              style={{
                width: 34, height: 34, borderRadius: 9, marginBottom: 10,
                background: 'transparent', border: 'none',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                cursor: 'pointer', padding: 0,
                transition: 'background 0.15s',
              }}
              onMouseEnter={e => { e.currentTarget.style.background = 'rgba(0,0,0,0.06)'; }}
              onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
            >
              <Menu style={{ width: 19, height: 19, color: '#0A0A0A', strokeWidth: 2 }} />
            </button>
          )}
          <button
            onClick={handleNew}
            title="New chat"
            style={{
              width: 36, height: 36, borderRadius: 9,
              background: '#fff', border: '1px solid rgba(0,0,0,0.06)',
              boxShadow: '0 1px 2px rgba(0,0,0,0.03)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'pointer', marginBottom: 10,
            }}
          >
            <Plus style={{ width: 14, height: 14, color: '#0A0A0A', strokeWidth: 2 }} />
          </button>
          {/* Top 8 recent chats as icons */}
          {filtered.slice(0, 8).map(item => {
            const Icon = iconForTypes(item.query_types);
            const isActive = item.history_id === selectedId;
            return (
              <button
                key={item.history_id}
                onClick={() => handleOpen(item)}
                title={item.query || '(Untitled)'}
                style={{
                  width: 36, height: 36, borderRadius: 9,
                  background: isActive ? '#fff' : 'transparent',
                  boxShadow: isActive ? '0 1px 2px rgba(0,0,0,0.04)' : 'none',
                  border: isActive ? '1px solid rgba(0,0,0,0.04)' : '1px solid transparent',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  cursor: 'pointer', transition: 'all 0.12s',
                }}
                onMouseEnter={e => { if (!isActive) e.currentTarget.style.background = 'rgba(0,0,0,0.03)'; }}
                onMouseLeave={e => { if (!isActive) e.currentTarget.style.background = 'transparent'; }}
              >
                <Icon style={{ width: 14, height: 14, color: isActive ? '#0A0A0A' : '#A8A8A8', strokeWidth: 1.7 }} />
              </button>
            );
          })}
          {filtered.length > 8 && (
            <div style={{
              fontSize: 9, color: '#BBB', fontFamily: "'JetBrains Mono', monospace",
              marginTop: 8, letterSpacing: '0.18em',
            }}>
              +{filtered.length - 8}
            </div>
          )}
        </div>
      )}

      {/* Expanded mode — full header, search, grouped list */}
      {!collapsed && (
      <>
      {/* Header — hamburger + title */}
      <div style={{ padding: '18px 12px 8px', flexShrink: 0, display: 'flex', alignItems: 'flex-start', gap: 8 }}>
        {onToggle && (
          <button
            onClick={onToggle}
            title="Collapse chats"
            aria-label="Collapse chats"
            style={{
              width: 34, height: 34, borderRadius: 9,
              background: 'transparent', border: 'none',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'pointer', padding: 0, flexShrink: 0, marginTop: 2,
              transition: 'background 0.15s',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(0,0,0,0.06)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
          >
            <Menu style={{ width: 19, height: 19, color: '#0A0A0A', strokeWidth: 2 }} />
          </button>
        )}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{
            fontSize: 11, fontWeight: 500, letterSpacing: '0.22em',
            color: '#A8A8A8', textTransform: 'uppercase', marginBottom: 2,
          }}>
            Spectr · History
          </div>
          <div style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: 17, fontWeight: 500, letterSpacing: '-0.035em',
            background: 'linear-gradient(to bottom right, #0A0A0A 40%, rgba(10,10,10,0.55))',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text',
          }}>
            Previous chats
          </div>
        </div>
      </div>

      {/* New + Search row */}
      <div style={{ padding: '0 10px 10px', flexShrink: 0, display: 'flex', flexDirection: 'column', gap: 6 }}>
        <button
          onClick={handleNew}
          style={{
            width: '100%', display: 'flex', alignItems: 'center', gap: 8,
            padding: '8px 11px', height: 36,
            background: '#FFFFFF',
            border: '1px solid rgba(0,0,0,0.06)',
            borderRadius: 9,
            fontSize: 12.5, fontWeight: 500, color: '#0A0A0A',
            fontFamily: "'Inter', sans-serif", cursor: 'pointer',
            boxShadow: '0 1px 2px rgba(0,0,0,0.03)',
            letterSpacing: '-0.005em',
            transition: 'all 0.15s',
          }}
          onMouseEnter={e => { e.currentTarget.style.background = '#F9F9F9'; e.currentTarget.style.borderColor = 'rgba(0,0,0,0.12)'; }}
          onMouseLeave={e => { e.currentTarget.style.background = '#FFFFFF'; e.currentTarget.style.borderColor = 'rgba(0,0,0,0.06)'; }}
        >
          <Plus style={{ width: 13, height: 13, strokeWidth: 2 }} />
          New chat
        </button>

        <div style={{ position: 'relative' }}>
          <Search style={{ width: 12, height: 12, position: 'absolute', left: 11, top: '50%', transform: 'translateY(-50%)', color: '#AAA' }} />
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Search chats…"
            style={{
              width: '100%', height: 34,
              padding: '0 10px 0 30px',
              background: '#FFFFFF',
              border: '1px solid rgba(0,0,0,0.06)',
              borderRadius: 9, fontSize: 12.5, color: '#0A0A0A',
              outline: 'none', fontFamily: "'Inter', sans-serif",
              letterSpacing: '-0.005em',
              boxShadow: '0 1px 2px rgba(0,0,0,0.03)',
            }}
          />
        </div>
      </div>

      {/* List */}
      <div className="pc-scroll" style={{ flex: 1, overflowY: 'auto', padding: '4px 6px 12px' }}>
        {loading && (
          <div style={{ padding: '4px 2px', display: 'flex', flexDirection: 'column', gap: 4 }}>
            <Skeleton.ChatRow />
            <Skeleton.ChatRow />
            <Skeleton.ChatRow />
            <Skeleton.ChatRow />
          </div>
        )}
        {!loading && filtered.length === 0 && (
          <div style={{
            padding: '40px 18px', textAlign: 'center',
            fontSize: 12, color: '#9A9A9A', lineHeight: 1.6,
          }}>
            <Clock style={{ width: 18, height: 18, color: '#CCC', marginBottom: 10, strokeWidth: 1.5 }} />
            <div>No previous chats yet.</div>
            <div style={{ fontSize: 11, color: '#BBB', marginTop: 4 }}>Your history will appear here.</div>
          </div>
        )}
        {!loading && sections.map((sec) => (
          <div key={sec} style={{ marginBottom: 10 }}>
            <div style={{
              fontSize: 10, fontWeight: 500,
              color: '#BBB', textTransform: 'uppercase', letterSpacing: '0.22em',
              padding: '8px 10px 6px',
            }}>
              {sec}
            </div>
            {grouped[sec].map((item) => {
              const Icon = iconForTypes(item.query_types);
              const isActive = item.history_id === selectedId;
              return (
                <button
                  key={item.history_id}
                  onClick={() => handleOpen(item)}
                  className={`pc-item${isActive ? ' active' : ''}`}
                  style={{
                    width: '100%', display: 'flex', alignItems: 'flex-start', gap: 9,
                    padding: '8px 10px', marginBottom: 1,
                    background: 'transparent', border: 'none',
                    borderRadius: 8, cursor: 'pointer',
                    textAlign: 'left', fontFamily: "'Inter', sans-serif",
                  }}
                >
                  <Icon style={{
                    width: 13, height: 13, color: isActive ? '#0A0A0A' : '#A8A8A8',
                    strokeWidth: 1.7, flexShrink: 0, marginTop: 2,
                  }} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                      fontSize: 12.5, fontWeight: isActive ? 550 : 450,
                      color: isActive ? '#0A0A0A' : '#333',
                      lineHeight: 1.4,
                      letterSpacing: '-0.005em',
                      overflow: 'hidden',
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical',
                    }}>
                      {item.query || '(Untitled)'}
                    </div>
                    <div style={{
                      display: 'flex', alignItems: 'center', gap: 7,
                      fontSize: 10, color: '#A8A8A8', marginTop: 3,
                      letterSpacing: '0.02em',
                    }}>
                      <span style={{ fontFamily: "'JetBrains Mono', monospace" }}>
                        {item.mode === 'partner' ? 'Deep' : 'Quick'}
                      </span>
                      {item.citations_count != null && (
                        <>
                          <span style={{ color: '#DDD' }}>·</span>
                          <span>{item.citations_count} cites</span>
                        </>
                      )}
                      <span style={{ color: '#DDD' }}>·</span>
                      <span>{new Date(item.created_at).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' })}</span>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        ))}
      </div>

      {/* Footer */}
      <div style={{
        padding: '10px 14px',
        flexShrink: 0,
        borderTop: '1px solid rgba(0,0,0,0.04)',
        fontSize: 10, color: '#A8A8A8',
        letterSpacing: '0.18em', textTransform: 'uppercase',
        display: 'flex', alignItems: 'center', gap: 6,
      }}>
        <FileText style={{ width: 11, height: 11, strokeWidth: 1.6 }} />
        {items.length} {items.length === 1 ? 'thread' : 'threads'}
      </div>
      </>
      )}
    </aside>
  );
}
