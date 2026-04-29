import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle, AlertCircle, Info, X } from 'lucide-react';

/**
 * Toast system — slide-up, stacked, auto-dismiss, liquid-glass finish.
 *
 * Usage:
 *   const toast = useToast();
 *   toast.success('Saved');
 *   toast.error('Upload failed', { desc: 'File exceeds 10MB' });
 *   toast.info('New update available');
 *
 * Every toast auto-dismisses after 4s (configurable). Click the × to dismiss
 * early. Multiple toasts stack bottom-up with a subtle scale-back effect on
 * the older ones — straight out of Apple's notification stacking playbook.
 */

const ToastContext = createContext(null);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within <ToastProvider>');
  return ctx;
}

const VARIANTS = {
  success: {
    icon: CheckCircle,
    iconColor: '#10B981',
    accent: 'rgba(16,185,129,0.9)',
    glow: '0 0 0 1px rgba(16,185,129,0.15), 0 12px 32px rgba(16,185,129,0.10)',
  },
  error: {
    icon: AlertCircle,
    iconColor: '#EF4444',
    accent: 'rgba(239,68,68,0.9)',
    glow: '0 0 0 1px rgba(239,68,68,0.18), 0 12px 32px rgba(239,68,68,0.12)',
  },
  info: {
    icon: Info,
    iconColor: '#0A0A0A',
    accent: 'rgba(10,10,10,0.7)',
    glow: '0 12px 32px rgba(0,0,0,0.12)',
  },
};

let toastCounter = 0;

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const dismiss = useCallback((id) => {
    setToasts(t => t.filter(x => x.id !== id));
  }, []);

  const push = useCallback((variant, title, opts = {}) => {
    const id = ++toastCounter;
    const duration = opts.duration ?? 4000;
    setToasts(t => [...t, { id, variant, title, desc: opts.desc, duration }]);
    if (duration > 0) setTimeout(() => dismiss(id), duration);
    return id;
  }, [dismiss]);

  const api = React.useMemo(() => ({
    success: (title, opts) => push('success', title, opts),
    error:   (title, opts) => push('error',   title, opts),
    info:    (title, opts) => push('info',    title, opts),
    dismiss,
  }), [push, dismiss]);

  return (
    <ToastContext.Provider value={api}>
      {children}
      <ToastViewport toasts={toasts} onDismiss={dismiss} />
    </ToastContext.Provider>
  );
}

function ToastViewport({ toasts, onDismiss }) {
  // Reverse so newest stack at the bottom closest to the viewport edge
  return (
    <div style={{
      position: 'fixed', bottom: 28, right: 28, zIndex: 10000,
      display: 'flex', flexDirection: 'column', gap: 10,
      alignItems: 'flex-end', pointerEvents: 'none',
    }}>
      <AnimatePresence initial={false}>
        {toasts.map((t, i) => {
          const v = VARIANTS[t.variant] || VARIANTS.info;
          const Icon = v.icon;
          // Older toasts scale down + dim — Apple stacking effect
          const age = toasts.length - 1 - i;
          return (
            <motion.div
              key={t.id}
              layout
              initial={{ opacity: 0, y: 30, scale: 0.94, filter: 'blur(6px)' }}
              animate={{ opacity: 1 - age * 0.08, y: 0, scale: 1 - age * 0.02, filter: 'blur(0px)' }}
              exit={{ opacity: 0, y: 10, scale: 0.96, filter: 'blur(4px)' }}
              transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
              style={{
                pointerEvents: 'auto',
                minWidth: 300, maxWidth: 440,
                padding: '13px 16px 13px 14px',
                background: 'rgba(255,255,255,0.82)',
                backdropFilter: 'blur(32px) saturate(180%)',
                WebkitBackdropFilter: 'blur(32px) saturate(180%)',
                border: '1px solid rgba(255,255,255,0.7)',
                borderLeft: `3px solid ${v.accent}`,
                borderRadius: 12,
                boxShadow: `${v.glow}, 0 20px 60px rgba(0,0,0,0.12)`,
                display: 'flex', alignItems: 'flex-start', gap: 11,
                fontFamily: "'Inter', sans-serif",
                color: '#0A0A0A',
              }}
            >
              <Icon style={{
                width: 16, height: 16, flexShrink: 0, marginTop: 1,
                color: v.iconColor, strokeWidth: 2,
              }} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{
                  fontSize: 13.5, fontWeight: 500, letterSpacing: '-0.005em',
                  lineHeight: 1.35, color: '#0A0A0A',
                }}>
                  {t.title}
                </div>
                {t.desc && (
                  <div style={{
                    fontSize: 12, color: '#6B7280', marginTop: 3,
                    lineHeight: 1.5, letterSpacing: '-0.002em',
                  }}>
                    {t.desc}
                  </div>
                )}
              </div>
              <button
                onClick={() => onDismiss(t.id)}
                aria-label="Dismiss"
                style={{
                  background: 'transparent', border: 'none', padding: 2, marginTop: -1,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  cursor: 'pointer', borderRadius: 4, flexShrink: 0,
                  transition: 'background 0.12s',
                }}
                onMouseEnter={e => { e.currentTarget.style.background = 'rgba(0,0,0,0.06)'; }}
                onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
              >
                <X style={{ width: 12, height: 12, color: '#6B7280', strokeWidth: 2 }} />
              </button>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
