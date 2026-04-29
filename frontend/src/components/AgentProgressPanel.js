import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, CheckCircle2, AlertCircle, Code, FileCheck, Play, X, ChevronDown } from 'lucide-react';

/**
 * Chronological agent progress panel. Renders SSE events from /api/agent/execute|iterate|route.
 *
 * Props:
 *   events: Array<{ type, iteration?, step?, message?, code?, exit_code?, stdout?, files?, invalid_files?, error? }>
 *   onDismiss?: () => void
 *   title?: string
 */
export function AgentProgressPanel({ events = [], onDismiss, title = 'Agent in progress' }) {
  const [expanded, setExpanded] = useState(true);
  const [codeExpanded, setCodeExpanded] = useState({});

  if (events.length === 0) return null;

  const isComplete = events.some(e => e.type === 'success' || e.type === 'error');
  const hasError = events.some(e => e.type === 'error');

  const renderEvent = (e, i) => {
    const base = {
      padding: '10px 14px',
      borderRadius: 10,
      fontSize: 12.5,
      fontFamily: "'Inter', sans-serif",
      display: 'flex', alignItems: 'flex-start', gap: 10,
      lineHeight: 1.5,
      marginBottom: 6,
    };

    switch (e.type) {
      case 'status':
        return (
          <motion.div key={i}
            initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
            style={{ ...base, background: '#FAFAFA', border: '1px solid #EBEBEB' }}>
            <Loader2 style={{ width: 13, height: 13, color: '#888', animation: 'spin 0.8s linear infinite', flexShrink: 0, marginTop: 2 }} />
            <div style={{ flex: 1 }}>
              {e.step && <span style={{ fontSize: 10, fontWeight: 700, color: '#AAA', letterSpacing: '.06em', textTransform: 'uppercase', marginRight: 6 }}>[{e.step}]</span>}
              <span style={{ color: '#444' }}>{e.message}</span>
            </div>
          </motion.div>
        );

      case 'code': {
        const open = codeExpanded[i];
        return (
          <motion.div key={i}
            initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
            style={{ ...base, background: '#0A0A0A', color: '#fff', flexDirection: 'column', alignItems: 'stretch', gap: 0 }}>
            <button onClick={() => setCodeExpanded(s => ({ ...s, [i]: !open }))}
              style={{
                display: 'flex', alignItems: 'center', gap: 8, background: 'transparent', border: 'none',
                color: '#fff', cursor: 'pointer', padding: 0, fontFamily: 'inherit', fontSize: 12.5, fontWeight: 500, textAlign: 'left', width: '100%',
              }}>
              <Code style={{ width: 13, height: 13, color: '#60A5FA', flexShrink: 0 }} />
              <span style={{ flex: 1 }}>
                Iteration {e.iteration || 1} — Python ({e.length} chars)
              </span>
              <ChevronDown style={{ width: 12, height: 12, transition: 'transform 0.2s', transform: open ? 'rotate(180deg)' : 'none' }} />
            </button>
            <AnimatePresence>
              {open && (
                <motion.pre
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  style={{
                    marginTop: 10, padding: 10, background: 'rgba(255,255,255,0.05)', borderRadius: 6,
                    fontSize: 11, color: '#E5E5E5', fontFamily: "'JetBrains Mono', monospace",
                    whiteSpace: 'pre-wrap', maxHeight: 280, overflowY: 'auto', margin: '10px 0 0',
                  }}>{e.code}</motion.pre>
              )}
            </AnimatePresence>
          </motion.div>
        );
      }

      case 'execution':
        return (
          <motion.div key={i}
            initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
            style={{ ...base, background: e.exit_code === 0 ? 'rgba(34,197,94,0.06)' : 'rgba(239,68,68,0.06)', border: `1px solid ${e.exit_code === 0 ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.2)'}` }}>
            <Play style={{ width: 13, height: 13, color: e.exit_code === 0 ? '#22C55E' : '#EF4444', flexShrink: 0, marginTop: 2 }} />
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600, color: '#333' }}>
                Execution: {e.exit_code === 0 ? 'Success' : `Exit code ${e.exit_code}`}
              </div>
              {e.stdout && (
                <pre style={{ marginTop: 6, padding: 8, background: 'rgba(0,0,0,0.04)', borderRadius: 4, fontSize: 11, fontFamily: "'JetBrains Mono', monospace", color: '#555', maxHeight: 120, overflowY: 'auto', whiteSpace: 'pre-wrap', margin: '6px 0 0' }}>
                  {e.stdout.slice(0, 500)}{e.stdout.length > 500 ? '\n... (truncated)' : ''}
                </pre>
              )}
            </div>
          </motion.div>
        );

      case 'output_files':
        return (
          <motion.div key={i}
            initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
            style={{ ...base, background: 'rgba(34,197,94,0.06)', border: '1px solid rgba(34,197,94,0.2)' }}>
            <FileCheck style={{ width: 13, height: 13, color: '#22C55E', flexShrink: 0, marginTop: 2 }} />
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600, color: '#333', marginBottom: 4 }}>
                {e.files?.length || 0} file{(e.files?.length || 0) !== 1 ? 's' : ''} produced
              </div>
              {e.files?.slice(0, 5).map((f, idx) => (
                <div key={idx} style={{ fontSize: 11, color: '#666', display: 'flex', gap: 6, alignItems: 'center' }}>
                  <span style={{ width: 3, height: 3, borderRadius: '50%', background: '#22C55E' }} />
                  <span style={{ fontFamily: "'JetBrains Mono', monospace" }}>{f.name || f}</span>
                  {f.size && <span style={{ color: '#AAA' }}>· {(f.size / 1024).toFixed(1)}KB</span>}
                </div>
              ))}
            </div>
          </motion.div>
        );

      case 'validation_retry':
        return (
          <motion.div key={i}
            initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
            style={{ ...base, background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.3)' }}>
            <AlertCircle style={{ width: 13, height: 13, color: '#F59E0B', flexShrink: 0, marginTop: 2 }} />
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600, color: '#92400E' }}>Validation retry</div>
              {e.invalid_files?.length > 0 && (
                <div style={{ fontSize: 11, color: '#B45309', marginTop: 3 }}>
                  {e.invalid_files.length} file(s) need fixing
                </div>
              )}
            </div>
          </motion.div>
        );

      case 'success':
        return (
          <motion.div key={i}
            initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
            style={{ ...base, background: '#0A0A0A', color: '#fff', border: '1px solid #0A0A0A' }}>
            <CheckCircle2 style={{ width: 14, height: 14, color: '#22C55E', flexShrink: 0, marginTop: 1 }} />
            <div style={{ flex: 1, fontWeight: 600 }}>
              Complete in {e.iterations || 1} iteration{(e.iterations || 1) !== 1 ? 's' : ''} — {e.files?.length || 0} file(s)
            </div>
          </motion.div>
        );

      case 'error':
        return (
          <motion.div key={i}
            initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
            style={{ ...base, background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.3)' }}>
            <AlertCircle style={{ width: 13, height: 13, color: '#EF4444', flexShrink: 0, marginTop: 2 }} />
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600, color: '#991B1B' }}>Failed</div>
              <div style={{ fontSize: 11, color: '#B91C1C', marginTop: 2 }}>{e.message || 'Unknown error'}</div>
            </div>
          </motion.div>
        );

      default:
        return (
          <motion.div key={i}
            initial={{ opacity: 0 }} animate={{ opacity: 1 }}
            style={{ ...base, background: '#FAFAFA', color: '#888' }}>
            <span style={{ flex: 1, fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}>{JSON.stringify(e).slice(0, 120)}</span>
          </motion.div>
        );
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 10 }}
      transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
      style={{
        borderRadius: 12,
        background: '#fff',
        border: '1px solid #EBEBEB',
        boxShadow: '0 4px 16px rgba(0,0,0,0.04)',
        overflow: 'hidden',
        fontFamily: "'Inter', sans-serif",
      }}>
      {/* Header */}
      <div style={{
        padding: '10px 14px', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        borderBottom: expanded ? '1px solid #F5F5F5' : 'none',
        background: '#FAFAFA',
      }}>
        <button onClick={() => setExpanded(!expanded)} style={{
          display: 'flex', alignItems: 'center', gap: 8, background: 'none', border: 'none', cursor: 'pointer',
          padding: 0, fontFamily: 'inherit', flex: 1, textAlign: 'left',
        }}>
          {!isComplete ? (
            <Loader2 style={{ width: 12, height: 12, color: '#0A0A0A', animation: 'spin 0.8s linear infinite' }} />
          ) : hasError ? (
            <AlertCircle style={{ width: 12, height: 12, color: '#EF4444' }} />
          ) : (
            <CheckCircle2 style={{ width: 12, height: 12, color: '#22C55E' }} />
          )}
          <span style={{ fontSize: 12, fontWeight: 700, color: '#0A0A0A' }}>{title}</span>
          <span style={{ fontSize: 11, color: '#888' }}>({events.length} step{events.length !== 1 ? 's' : ''})</span>
          <ChevronDown style={{ width: 11, height: 11, color: '#AAA', marginLeft: 'auto', transition: 'transform 0.2s', transform: expanded ? 'none' : 'rotate(-90deg)' }} />
        </button>
        {onDismiss && isComplete && (
          <button onClick={onDismiss} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4, color: '#888', marginLeft: 6 }}>
            <X style={{ width: 12, height: 12 }} />
          </button>
        )}
      </div>
      {/* Events list */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0 }} animate={{ height: 'auto' }} exit={{ height: 0 }}
            style={{ overflow: 'hidden' }}>
            <div style={{ padding: 10, maxHeight: 400, overflowY: 'auto' }}>
              {events.map(renderEvent)}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

/**
 * useAgentStream — hook that connects to an SSE endpoint and accumulates events
 */
export function useAgentStream() {
  const [events, setEvents] = useState([]);
  const [running, setRunning] = useState(false);

  const reset = () => setEvents([]);

  const connect = async (url, token, body) => {
    setRunning(true);
    setEvents([]);
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(body),
      });
      if (!res.ok || !res.body) throw new Error(`Stream failed: ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;
          const dataStr = trimmed.startsWith('data:') ? trimmed.slice(5).trim() : trimmed;
          if (dataStr === '[DONE]') continue;
          try {
            const evt = JSON.parse(dataStr);
            setEvents(prev => [...prev, evt]);
          } catch { /* skip non-JSON */ }
        }
      }
    } catch (e) {
      setEvents(prev => [...prev, { type: 'error', message: e.message || 'Stream error' }]);
    } finally {
      setRunning(false);
    }
  };

  return { events, running, connect, reset };
}
