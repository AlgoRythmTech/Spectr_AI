import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence, useInView } from 'framer-motion';
import { Scale, ArrowUp, Sparkles, Bot, Send } from 'lucide-react';

const EASE = [0.16, 1, 0.3, 1];

/**
 * Spectr AI Interactive Demo — A branded AI chat experience
 * Shows Spectr introducing itself with typing animations.
 * Pure JS/inline styles for CRA.
 */

const DEMO_MESSAGES = [
  {
    role: 'user',
    text: 'What is Spectr?',
    delay: 800,
  },
  {
    role: 'ai',
    text: "I'm Spectr — India's AI-native legal intelligence platform. I can research 50 million court judgments, review contracts for risks, reconcile your GST data, and draft legal memos — all in minutes, not days.",
    delay: 1200,
  },
  {
    role: 'user',
    text: 'Can you find landmark privacy judgments?',
    delay: 2000,
  },
  {
    role: 'ai',
    text: 'Found 3 landmark judgments on the right to privacy under Article 21:\n\n1. K.S. Puttaswamy v. Union of India (2017) — 9-judge bench unanimously held privacy as a fundamental right\n2. Maneka Gandhi v. Union of India (1978) — Expanded Article 21 to include personal liberty\n3. Gobind v. State of MP (1975) — First recognition of privacy as implicit in Article 21\n\nAll citations verified against Supreme Court database. 98% confidence.',
    delay: 1800,
  },
];

function TypingIndicator() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      style={{ display: 'flex', gap: 4, padding: '12px 16px' }}
    >
      {[0, 1, 2].map(i => (
        <motion.div
          key={i}
          animate={{ y: [0, -6, 0], opacity: [0.3, 1, 0.3] }}
          transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.15 }}
          style={{
            width: 6, height: 6, borderRadius: '50%',
            background: 'rgba(255,255,255,0.4)',
          }}
        />
      ))}
    </motion.div>
  );
}

function TypeWriter({ text, speed = 20, onComplete }) {
  const [displayed, setDisplayed] = useState('');
  const idx = useRef(0);

  useEffect(() => {
    idx.current = 0;
    setDisplayed('');
    const iv = setInterval(() => {
      idx.current++;
      if (idx.current >= text.length) {
        setDisplayed(text);
        clearInterval(iv);
        if (onComplete) onComplete();
      } else {
        setDisplayed(text.slice(0, idx.current));
      }
    }, speed);
    return () => clearInterval(iv);
  }, [text, speed, onComplete]);

  return (
    <span>
      {displayed}
      {displayed.length < text.length && (
        <motion.span
          animate={{ opacity: [1, 0] }}
          transition={{ duration: 0.5, repeat: Infinity }}
          style={{ display: 'inline-block', width: 2, height: '1em', background: '#fff', marginLeft: 2, verticalAlign: 'text-bottom' }}
        />
      )}
    </span>
  );
}

export function SpectrAIDemo({ style }) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-100px' });
  const [visibleMessages, setVisibleMessages] = useState([]);
  const [isTyping, setIsTyping] = useState(false);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [inputValue, setInputValue] = useState('');
  const [inputFocused, setInputFocused] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (!inView) return;
    if (currentIdx >= DEMO_MESSAGES.length) return;

    const msg = DEMO_MESSAGES[currentIdx];
    const timer = setTimeout(() => {
      if (msg.role === 'ai') {
        setIsTyping(true);
        setTimeout(() => {
          setIsTyping(false);
          setVisibleMessages(prev => [...prev, msg]);
          setCurrentIdx(i => i + 1);
        }, 1500);
      } else {
        setVisibleMessages(prev => [...prev, msg]);
        setCurrentIdx(i => i + 1);
      }
    }, msg.delay);

    return () => clearTimeout(timer);
  }, [inView, currentIdx]);

  useEffect(() => {
    // Scroll only within the chat container, NOT the whole page
    const el = messagesEndRef.current;
    if (el && el.parentElement) {
      el.parentElement.scrollTop = el.parentElement.scrollHeight;
    }
  }, [visibleMessages, isTyping]);

  return (
    <div ref={ref} style={{ width: '100%', maxWidth: 680, margin: '0 auto', ...style }}>
      {/* Window chrome */}
      <motion.div
        initial={{ opacity: 0, y: 40, scale: 0.95 }}
        whileInView={{ opacity: 1, y: 0, scale: 1 }}
        viewport={{ once: true, margin: '-60px' }}
        transition={{ duration: 0.8, ease: EASE }}
        style={{
          background: '#0a0a0a',
          borderRadius: 20,
          border: '1px solid rgba(255,255,255,0.08)',
          overflow: 'hidden',
          boxShadow: '0 40px 120px rgba(0,0,0,0.6), 0 0 80px rgba(255,255,255,0.02)',
        }}
      >
        {/* Title bar */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '14px 20px', borderBottom: '1px solid rgba(255,255,255,0.06)',
          background: 'rgba(255,255,255,0.02)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <div>
              <div style={{ fontSize: 15, fontWeight: 500, color: '#fff', fontFamily: "'Inter', sans-serif", letterSpacing: '-0.04em' }}>Spectr AI</div>
              <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.3)', display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#22c55e', display: 'inline-block' }} />
                Online
              </div>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            {['#333', '#333', '#333'].map((c, i) => (
              <div key={i} style={{ width: 10, height: 10, borderRadius: '50%', background: c, border: '1px solid rgba(255,255,255,0.06)' }} />
            ))}
          </div>
        </div>

        {/* Messages */}
        <div style={{
          minHeight: 320, maxHeight: 420, overflowY: 'auto',
          padding: '24px 20px', display: 'flex', flexDirection: 'column', gap: 16,
        }}>
          {/* Welcome message */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.5 }}
            style={{
              textAlign: 'center', padding: '20px 16px', marginBottom: 8,
            }}
          >
            <motion.div
              animate={{ rotate: [0, 5, -5, 0] }}
              transition={{ duration: 3, repeat: Infinity, repeatDelay: 2 }}
              style={{
                width: 44, height: 44, borderRadius: 14,
                background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                margin: '0 auto 16px',
              }}
            >
              <Sparkles style={{ width: 20, height: 20, color: 'rgba(255,255,255,0.5)' }} />
            </motion.div>
            <div style={{ fontSize: 14, color: 'rgba(255,255,255,0.3)', lineHeight: 1.6 }}>
              Welcome to <span style={{ color: '#fff', fontWeight: 600 }}>Spectr AI</span>
              <br />
              <span style={{ fontSize: 12 }}>India's most advanced legal intelligence</span>
            </div>
          </motion.div>

          <AnimatePresence>
            {visibleMessages.map((msg, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 14, scale: 0.97 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{ duration: 0.4, ease: EASE }}
                style={{
                  display: 'flex',
                  justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                  gap: 10,
                }}
              >
                {msg.role === 'ai' && (
                  <div style={{
                    width: 26, height: 26, borderRadius: 8, flexShrink: 0,
                    background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.08)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', marginTop: 2,
                  }}>
                    <Scale style={{ width: 11, height: 11, color: '#fff', strokeWidth: 2 }} />
                  </div>
                )}
                <div style={{
                  maxWidth: msg.role === 'user' ? '75%' : '85%',
                  padding: '12px 16px',
                  borderRadius: msg.role === 'user' ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
                  background: msg.role === 'user' ? 'rgba(255,255,255,0.08)' : 'rgba(255,255,255,0.03)',
                  border: `1px solid rgba(255,255,255,${msg.role === 'user' ? '0.1' : '0.05'})`,
                  fontSize: 13, color: msg.role === 'user' ? 'rgba(255,255,255,0.8)' : 'rgba(255,255,255,0.65)',
                  lineHeight: 1.7, whiteSpace: 'pre-wrap',
                  fontFamily: "'Plus Jakarta Sans', sans-serif",
                }}>
                  {i === visibleMessages.length - 1 && msg.role === 'ai' ? (
                    <TypeWriter text={msg.text} speed={15} />
                  ) : msg.text}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {/* Typing indicator */}
          <AnimatePresence>
            {isTyping && (
              <motion.div style={{ display: 'flex', gap: 10 }}>
                <div style={{
                  width: 26, height: 26, borderRadius: 8, flexShrink: 0,
                  background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.08)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  <Scale style={{ width: 11, height: 11, color: '#fff', strokeWidth: 2 }} />
                </div>
                <TypingIndicator />
              </motion.div>
            )}
          </AnimatePresence>

          <div ref={messagesEndRef} />
        </div>

        {/* Input bar */}
        <div style={{
          padding: '12px 16px', borderTop: '1px solid rgba(255,255,255,0.06)',
          background: 'rgba(255,255,255,0.02)',
        }}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 10,
            padding: '10px 14px', borderRadius: 14,
            background: 'rgba(255,255,255,0.04)',
            border: `1px solid rgba(255,255,255,${inputFocused ? '0.12' : '0.06'})`,
            transition: 'border-color 0.3s',
          }}>
            <input
              value={inputValue}
              onChange={e => setInputValue(e.target.value)}
              onFocus={() => setInputFocused(true)}
              onBlur={() => setInputFocused(false)}
              placeholder="Ask Spectr anything about Indian law..."
              style={{
                flex: 1, background: 'transparent', border: 'none', outline: 'none',
                color: 'rgba(255,255,255,0.7)', fontSize: 13,
                fontFamily: "'Plus Jakarta Sans', sans-serif",
              }}
            />
            <motion.div
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              style={{
                width: 30, height: 30, borderRadius: 10,
                background: inputValue ? '#fff' : 'rgba(255,255,255,0.08)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                cursor: 'pointer', transition: 'background 0.3s',
              }}
            >
              <ArrowUp style={{
                width: 14, height: 14,
                color: inputValue ? '#000' : 'rgba(255,255,255,0.3)',
                strokeWidth: 2,
              }} />
            </motion.div>
          </div>
          <div style={{
            textAlign: 'center', fontSize: 10,
            color: 'rgba(255,255,255,0.15)', marginTop: 8,
          }}>
            Spectr AI &middot; Powered by 50M+ Indian court judgments
          </div>
        </div>
      </motion.div>
    </div>
  );
}
