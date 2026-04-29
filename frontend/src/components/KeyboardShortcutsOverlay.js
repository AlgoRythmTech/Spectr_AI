import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Command, X } from 'lucide-react';

/**
 * KeyboardShortcutsOverlay — press `?` anywhere in the app to reveal.
 *
 * Beautiful Linear/Notion-style panel: liquid-glass card, grouped
 * shortcut list with proper <kbd> keycaps. Press `?` or `Esc` to dismiss.
 */

const SHORTCUTS = [
  {
    section: 'General',
    items: [
      { keys: ['⌘', 'K'], desc: 'Open command palette' },
      { keys: ['?'], desc: 'Show / hide keyboard shortcuts' },
      { keys: ['Esc'], desc: 'Close any dialog / dropdown' },
    ],
  },
  {
    section: 'Navigation',
    items: [
      { keys: ['G', 'A'], desc: 'Go to Assistant' },
      { keys: ['G', 'L'], desc: 'Go to Legal Research' },
      { keys: ['G', 'D'], desc: 'Go to Documents' },
      { keys: ['G', 'R'], desc: 'Go to Reconciler' },
      { keys: ['G', 'W'], desc: 'Go to Workflows' },
      { keys: ['G', 'H'], desc: 'Go to History' },
    ],
  },
  {
    section: 'Chat',
    items: [
      { keys: ['N'], desc: 'New chat' },
      { keys: ['⌘', 'Enter'], desc: 'Send message' },
      { keys: ['↑'], desc: 'Edit last message' },
      { keys: ['⌘', '⇧', 'C'], desc: 'Copy last AI response' },
    ],
  },
  {
    section: 'Layout',
    items: [
      { keys: ['⌘', '\\'], desc: 'Toggle left sidebar (chats)' },
      { keys: ['⌘', '.'], desc: 'Toggle right sidebar (nav)' },
    ],
  },
];

function Kbd({ children }) {
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      minWidth: 22, height: 22, padding: '0 6px',
      fontFamily: "'JetBrains Mono', monospace",
      fontSize: 11, fontWeight: 500,
      color: '#0A0A0A',
      background: '#FFFFFF',
      border: '1px solid rgba(0,0,0,0.12)',
      borderBottomWidth: 2,
      borderRadius: 5,
      letterSpacing: 0,
    }}>
      {children}
    </span>
  );
}

export default function KeyboardShortcutsOverlay() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onKey = (e) => {
      // Ignore when typing in inputs
      const target = e.target;
      const tag = (target?.tagName || '').toLowerCase();
      if (tag === 'input' || tag === 'textarea' || target?.isContentEditable) return;

      if (e.key === '?') {
        e.preventDefault();
        setOpen(o => !o);
      }
      if (e.key === 'Escape') setOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
          onClick={() => setOpen(false)}
          style={{
            position: 'fixed', inset: 0, zIndex: 9997,
            background: 'rgba(10,10,10,0.5)',
            backdropFilter: 'blur(14px) saturate(140%)',
            WebkitBackdropFilter: 'blur(14px) saturate(140%)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            padding: 24,
            fontFamily: "'Inter', sans-serif",
          }}
        >
          <motion.div
            onClick={e => e.stopPropagation()}
            initial={{ opacity: 0, y: 16, scale: 0.97, filter: 'blur(8px)' }}
            animate={{ opacity: 1, y: 0, scale: 1, filter: 'blur(0px)' }}
            exit={{ opacity: 0, y: 10, scale: 0.98 }}
            transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
            style={{
              width: '100%', maxWidth: 560, maxHeight: '82vh',
              background: 'rgba(255,255,255,0.86)',
              backdropFilter: 'blur(40px) saturate(180%)',
              WebkitBackdropFilter: 'blur(40px) saturate(180%)',
              border: '1px solid rgba(255,255,255,0.7)',
              borderRadius: 20,
              boxShadow: '0 40px 80px rgba(0,0,0,0.22), 0 8px 24px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.9)',
              overflow: 'hidden',
              display: 'flex', flexDirection: 'column',
            }}
          >
            {/* Header */}
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '22px 26px 16px',
              borderBottom: '1px solid rgba(0,0,0,0.05)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{
                  width: 32, height: 32, borderRadius: 9,
                  background: 'linear-gradient(135deg, #0A0A0A, #2B2B2B)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  <Command style={{ width: 15, height: 15, color: '#fff', strokeWidth: 2 }} />
                </div>
                <div>
                  <div style={{
                    fontFamily: "'Inter', sans-serif",
                    fontSize: 18, fontWeight: 500, letterSpacing: '-0.03em',
                    color: '#0A0A0A', lineHeight: 1.2,
                  }}>
                    Keyboard shortcuts
                  </div>
                  <div style={{
                    fontSize: 11, color: '#9CA3AF',
                    letterSpacing: '0.18em', textTransform: 'uppercase',
                    fontFamily: "'JetBrains Mono', monospace",
                    marginTop: 2,
                  }}>
                    Press <span style={{ color: '#0A0A0A' }}>?</span> anywhere
                  </div>
                </div>
              </div>
              <button
                onClick={() => setOpen(false)}
                aria-label="Close"
                style={{
                  width: 30, height: 30, borderRadius: 8,
                  background: 'transparent', border: 'none',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  cursor: 'pointer', padding: 0,
                  transition: 'background 0.12s',
                }}
                onMouseEnter={e => { e.currentTarget.style.background = 'rgba(0,0,0,0.06)'; }}
                onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
              >
                <X style={{ width: 14, height: 14, color: '#6B7280', strokeWidth: 2 }} />
              </button>
            </div>

            {/* Body — grouped sections */}
            <div style={{
              padding: '18px 26px 22px', overflowY: 'auto',
              display: 'flex', flexDirection: 'column', gap: 20,
            }}>
              {SHORTCUTS.map(group => (
                <div key={group.section}>
                  <div style={{
                    fontSize: 10, fontWeight: 500, color: '#9CA3AF',
                    letterSpacing: '0.22em', textTransform: 'uppercase',
                    marginBottom: 10,
                  }}>
                    {group.section}
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {group.items.map((s, i) => (
                      <div key={i} style={{
                        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                        gap: 18,
                      }}>
                        <span style={{
                          fontSize: 13.5, color: '#1F2937',
                          letterSpacing: '-0.005em',
                        }}>
                          {s.desc}
                        </span>
                        <span style={{ display: 'inline-flex', gap: 4, flexShrink: 0 }}>
                          {s.keys.map((k, ki) => (
                            <React.Fragment key={ki}>
                              {ki > 0 && <span style={{ color: '#D1D5DB', fontSize: 11 }}>+</span>}
                              <Kbd>{k}</Kbd>
                            </React.Fragment>
                          ))}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
