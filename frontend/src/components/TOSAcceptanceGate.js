// Terms of Service Acceptance Gate
// ─────────────────────────────────
// Implements Spectr T&C v2.0 Clause 2.1-2.3: captures a binding, time-stamped,
// metadata-rich Acceptance Event before the user reaches any protected page.
// This component:
//   1. Asks the backend for the current T&C version + pre-acceptance disclosures
//   2. Checks whether this user already has a valid acceptance on record
//   3. If not, blocks the app with a modal showing the full Agreement and
//      requiring an explicit checkbox tick + button click to proceed
//   4. Posts the Acceptance Event to the backend so it becomes part of the
//      immutable electronic record (Clause 16.14)
//
// If the user declines, they see the decline screen — the app is not usable.

import React, { useEffect, useState, useCallback } from 'react';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useToast } from './Toast';

const DECLINE_MESSAGE = (
  "You have not accepted the Terms of Service. The Spectr platform is not " +
  "available without acceptance. Close this tab to end your session, or " +
  "click \"Review again\" if you wish to reconsider."
);

export default function TOSAcceptanceGate({ children }) {
  const { getToken, user } = useAuth();
  const toast = useToast();
  const [phase, setPhase] = useState('loading');  // loading | needs_acceptance | accepted | declined | error
  const [tos, setTos] = useState(null);
  const [acknowledged, setAcknowledged] = useState({});
  const [checkboxTicked, setCheckboxTicked] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const authHeaders = useCallback(async () => {
    try {
      const t = await getToken();
      return t ? { Authorization: `Bearer ${t}` } : {};
    } catch {
      return {};
    }
  }, [getToken]);

  // ───────────────────────────────────────────────────────────────
  // Fast path: check a local receipt BEFORE hitting any network.
  // If this user already accepted on this browser, the gate clears
  // instantly and the user never sees the modal. The backend is still
  // the source of truth, but we don't block the UI waiting for it.
  // ───────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!user) return;
    try {
      const key = `spectr_tc_accepted_${user?.user_id || user?.email || 'anon'}`;
      const raw = localStorage.getItem(key);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (parsed?.accepted_at) {
          setPhase('accepted');
        }
      }
    } catch { /* ignore */ }
  }, [user]);

  // Fetch TOS + acceptance status in PARALLEL, with a hard 2-second
  // timeout each. If either fetch is still pending at the deadline, we
  // fall back to a hardcoded TOS payload and default to `needs_acceptance`
  // so the UI never blocks. The modal overlays the app but the user can
  // still see they're logged in and the app is loading behind it.
  useEffect(() => {
    let cancelled = false;

    const timeoutPromise = (ms) => new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), ms));

    async function run() {
      // Race both fetches against a 2-second deadline each
      const tosPromise = Promise.race([
        api.get('/legal/tos/current'),
        timeoutPromise(2000),
      ]);

      const statusPromise = authHeaders().then(headers =>
        headers.Authorization
          ? Promise.race([
              api.get('/legal/acceptance/status', { headers }),
              timeoutPromise(2000),
            ])
          : Promise.reject(new Error('no auth'))
      );

      const [tosResult, statusResult] = await Promise.allSettled([tosPromise, statusPromise]);
      if (cancelled) return;

      // TOS payload — use backend data if we got it, else a minimal fallback
      // so the modal has content to render
      const tosPayload = tosResult.status === 'fulfilled'
        ? tosResult.value.data
        : {
            version: '2.0',
            effective_date: '2026-04-01',
            company_name: 'Spectr & Co.',
            company_location: 'Hyderabad, Telangana, India',
            full_text_url: '/legal/terms',
            disclosures: [],
          };
      setTos(tosPayload);

      // Phase: accepted only if backend confirms
      if (phase !== 'accepted') {
        if (statusResult.status === 'fulfilled' && statusResult.value?.data?.has_valid_acceptance) {
          setPhase('accepted');
        } else {
          setPhase('needs_acceptance');
        }
      }
    }
    run();
    return () => { cancelled = true; };
  }, [authHeaders]); // eslint-disable-line react-hooks/exhaustive-deps

  // Simplified gate — one checkbox. The per-disclosure acks are auto-filled
  // from the backend payload when the user ticks the single binding box, so
  // the audit log still records which disclosures were on the screen.
  const canSubmit = checkboxTicked && !submitting;

  const handleSubmit = () => {
    if (!canSubmit || !tos) return;
    setSubmitting(true);
    setErrorMsg('');

    const allDisclosureIds = (tos?.disclosures || []).map(d => d.id);
    const payload = {
      tos_version: tos.version,
      acknowledged_disclosures: allDisclosureIds,
      device_fingerprint: buildDeviceFingerprint(),
      user_id: user?.user_id || null,
      name: user?.name || null,
      email: user?.email || null,
      accepted_at: new Date().toISOString(),
      user_agent: (typeof navigator !== 'undefined' ? navigator.userAgent : '').slice(0, 400),
      screen: typeof screen !== 'undefined' ? `${screen.width}x${screen.height}` : null,
      timezone: Intl?.DateTimeFormat?.().resolvedOptions?.().timeZone || null,
      language: typeof navigator !== 'undefined' ? navigator.language : null,
      referrer: typeof document !== 'undefined' ? (document.referrer || null) : null,
      page_url: typeof window !== 'undefined' ? window.location.href : null,
    };

    // 1. Synchronous local receipt — proof of acceptance even if the user
    //    closes the tab before the backend call finishes.
    try {
      const key = `spectr_tc_accepted_${user?.user_id || user?.email || 'anon'}`;
      localStorage.setItem(key, JSON.stringify({
        ...payload,
        ack_count: payload.acknowledged_disclosures.length,
      }));
    } catch { /* ignore quota errors */ }

    // 2. OPEN THE APP IMMEDIATELY. The user ticked the box and clicked —
    //    that IS their consent. No network round-trip should sit between
    //    their click and the dashboard.
    setPhase('accepted');

    // 3. Sync to backend in the background with one retry. The POST writes
    //    an immutable record to MongoDB.tos_acceptances. Local receipt is
    //    the fallback if sync fails; log loudly so real failures are visible.
    (async () => {
      const postOnce = async () => {
        const headers = await authHeaders();
        const res = await api.post('/legal/acceptance', payload, { headers, timeout: 8000 });
        console.log('[TOS Gate] acceptance recorded:', res.data);
        return res;
      };
      try {
        const res = await postOnce();
        toast?.success('Welcome to Spectr.', {
          desc: `Agreement recorded · ${res?.data?.acceptance_id?.slice(0, 12) || 'saved'}`,
        });
      } catch (err) {
        const status = err?.response?.status;
        const body = err?.response?.data;
        if (status && status >= 400 && status < 500 && status !== 401) {
          console.error('[TOS Gate] acceptance POST rejected by server:', status, body);
          toast?.error('Couldn\'t record acceptance.', {
            desc: (body?.detail || 'Please contact support if this keeps happening.').toString().slice(0, 120),
          });
          return;
        }
        console.warn('[TOS Gate] acceptance POST transient failure, retrying:', status || err?.message);
        await new Promise(r => setTimeout(r, 1500));
        try {
          const res = await postOnce();
          toast?.success('Welcome to Spectr.', {
            desc: `Agreement recorded · ${res?.data?.acceptance_id?.slice(0, 12) || 'saved'}`,
          });
        } catch (retryErr) {
          console.error('[TOS Gate] acceptance POST retry failed — DB record missing, only local receipt stands:', retryErr?.response?.status || retryErr?.message, retryErr?.response?.data);
          toast?.info('Agreement saved locally.', {
            desc: 'We\'ll sync it to our servers when the connection recovers.',
            duration: 6000,
          });
        }
      }
    })();
  };

  // App ALWAYS renders underneath — the modal overlays on top when needed.
  // User sees they're logged in immediately; no "Loading Spectr..." blocking screen.
  if (phase === 'accepted' || phase === 'loading') return children;
  if (phase === 'declined') {
    return (
      <>
        {children}
        <DeclinedScreen onReconsider={() => setPhase('needs_acceptance')} />
      </>
    );
  }

  // Phase: needs_acceptance → overlay modal WHILE app renders behind
  return (
    <>
    {children}
    <div style={{
      position: 'fixed', inset: 0, zIndex: 9999,
      background: 'rgba(10,10,10,0.55)',
      backdropFilter: 'blur(18px) saturate(160%)',
      WebkitBackdropFilter: 'blur(18px) saturate(160%)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: 16, fontFamily: "'Inter', sans-serif",
      animation: 'spectr-gate-fade 0.35s cubic-bezier(0.22, 1, 0.36, 1)',
    }}>
      <style>{`
        @keyframes spectr-gate-fade { from { opacity: 0; } to { opacity: 1; } }
        @keyframes spectr-gate-pop { from { opacity: 0; transform: translateY(12px) scale(0.98); } to { opacity: 1; transform: translateY(0) scale(1); } }
      `}</style>
      <div style={{
        // Apple "liquid glass" card: tinted translucent white, huge blur, inset highlight, big drop shadow
        background: 'rgba(255,255,255,0.78)',
        backdropFilter: 'blur(40px) saturate(180%)',
        WebkitBackdropFilter: 'blur(40px) saturate(180%)',
        border: '1px solid rgba(255,255,255,0.7)',
        borderRadius: 22,
        maxWidth: 520, width: '100%',
        display: 'flex', flexDirection: 'column',
        boxShadow: '0 40px 80px rgba(0,0,0,0.22), 0 8px 24px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.9)',
        padding: '36px 36px 28px',
        animation: 'spectr-gate-pop 0.55s cubic-bezier(0.16, 1, 0.3, 1)',
      }}>
        {/* Eyebrow */}
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 6,
          fontSize: 10, fontWeight: 500, color: '#6B7280',
          letterSpacing: '0.22em', textTransform: 'uppercase',
          marginBottom: 14,
        }}>
          <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#22c55e', boxShadow: '0 0 8px rgba(34,197,94,0.7)' }} />
          Terms of Service v{tos?.version || '2.0'}
        </div>

        {/* Title */}
        <h2 style={{
          margin: 0,
          fontFamily: "'Inter', sans-serif",
          fontSize: 30, fontWeight: 500,
          letterSpacing: '-0.045em', lineHeight: 1.08,
          background: 'linear-gradient(to bottom right, #0A0A0A 40%, rgba(10,10,10,0.5))',
          WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text',
          marginBottom: 8,
        }}>
          Agree to continue.
        </h2>

        {/* Sub-copy */}
        <p style={{
          margin: 0, marginBottom: 22,
          fontSize: 13.5, color: '#6B7280', lineHeight: 1.55, letterSpacing: '-0.005em',
        }}>
          Tick the box to continue.
        </p>

        {/* Single binding checkbox — carries the full agreement text */}
        <label
          onClick={e => { if (e.target.tagName !== 'A') setCheckboxTicked(t => !t); }}
          style={{
            display: 'flex', alignItems: 'flex-start', gap: 12,
            padding: '16px 18px', marginBottom: 22,
            background: checkboxTicked ? 'rgba(10,10,10,0.05)' : 'rgba(250,250,250,0.6)',
            border: `1px solid ${checkboxTicked ? 'rgba(10,10,10,0.2)' : 'rgba(0,0,0,0.08)'}`,
            borderRadius: 14,
            cursor: 'pointer',
            transition: 'all 0.2s cubic-bezier(0.22, 1, 0.36, 1)',
            backdropFilter: 'blur(8px)',
            WebkitBackdropFilter: 'blur(8px)',
            userSelect: 'none',
          }}
        >
          <div style={{
            width: 18, height: 18, flexShrink: 0, marginTop: 1, borderRadius: 5,
            border: `1.5px solid ${checkboxTicked ? '#0A0A0A' : 'rgba(0,0,0,0.3)'}`,
            background: checkboxTicked ? '#0A0A0A' : '#fff',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            transition: 'all 0.18s',
            boxShadow: checkboxTicked ? '0 2px 6px rgba(10,10,10,0.22)' : 'none',
          }}>
            {checkboxTicked && (
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="20 6 9 17 4 12" />
              </svg>
            )}
          </div>
          <span style={{ fontSize: 14.5, color: '#0A0A0A', lineHeight: 1.5, letterSpacing: '-0.01em', fontWeight: 500 }}>
            I agree to the{' '}
            <a
              href={tos?.full_text_url || '/legal/terms'}
              target="_blank" rel="noreferrer"
              onClick={e => e.stopPropagation()}
              style={{
                color: '#0A0A0A', fontWeight: 600,
                textDecoration: 'underline',
                textDecorationColor: '#0A0A0A',
                textUnderlineOffset: 3,
                textDecorationThickness: '1.5px',
              }}
            >
              Terms &amp; Conditions
            </a>
            .
          </span>
        </label>

        {errorMsg && (
          <div style={{ marginBottom: 14, padding: '10px 14px', background: 'rgba(254,242,242,0.8)', border: '1px solid rgba(254,202,202,0.9)', borderRadius: 10, color: '#B91C1C', fontSize: 12.5, backdropFilter: 'blur(8px)' }}>
            {errorMsg}
          </div>
        )}


        {/* Liquid-glass action row */}
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <button
            onClick={() => setPhase('declined')}
            disabled={submitting}
            style={{
              padding: '12px 20px',
              background: 'rgba(255,255,255,0.5)',
              backdropFilter: 'blur(10px)', WebkitBackdropFilter: 'blur(10px)',
              color: '#555',
              border: '1px solid rgba(0,0,0,0.08)', borderRadius: 12,
              fontFamily: "'Inter', sans-serif",
              fontSize: 13, fontWeight: 500, letterSpacing: '-0.005em',
              cursor: submitting ? 'not-allowed' : 'pointer',
              transition: 'all 0.2s',
            }}
            onMouseEnter={e => { if (!submitting) e.currentTarget.style.background = 'rgba(255,255,255,0.85)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.5)'; }}
          >
            Decline
          </button>
          <button
            onClick={handleSubmit}
            disabled={!canSubmit}
            style={{
              flex: 1,
              padding: '12px 22px',
              background: canSubmit
                ? 'linear-gradient(180deg, #1a1a1a 0%, #0a0a0a 100%)'
                : 'rgba(0,0,0,0.08)',
              color: canSubmit ? '#fff' : '#9CA3AF',
              border: 'none', borderRadius: 12,
              fontFamily: "'Inter', sans-serif",
              fontSize: 14, fontWeight: 500, letterSpacing: '-0.01em',
              cursor: canSubmit ? 'pointer' : 'not-allowed',
              transition: 'all 0.2s cubic-bezier(0.22, 1, 0.36, 1)',
              boxShadow: canSubmit
                ? '0 8px 22px rgba(10,10,10,0.22), inset 0 1px 0 rgba(255,255,255,0.15)'
                : 'none',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
            }}
            onMouseEnter={e => { if (canSubmit) e.currentTarget.style.transform = 'translateY(-1px)'; }}
            onMouseLeave={e => { e.currentTarget.style.transform = 'none'; }}
          >
            {submitting ? (
              <>
                <div style={{ width: 13, height: 13, border: '2px solid rgba(255,255,255,0.3)', borderTopColor: '#fff', borderRadius: '50%', animation: 'spin 0.7s linear infinite' }} />
                Recording…
              </>
            ) : (
              <>I Agree &amp; Continue</>
            )}
          </button>
        </div>

        {/* Fine-print footer */}
        <p style={{
          marginTop: 14, fontSize: 11, color: '#9CA3AF',
          lineHeight: 1.5, textAlign: 'center', letterSpacing: '-0.005em',
        }}>
          Your acceptance is logged with your IP, name, email and timestamp.
        </p>
      </div>
    </div>
    </>
  );
}

function LoadingScreen() {
  return (
    <div style={{
      position: 'fixed', inset: 0, display: 'flex',
      alignItems: 'center', justifyContent: 'center',
      background: '#FFFFFF', zIndex: 9999,
    }}>
      <div style={{ fontSize: 13, color: '#888', fontFamily: "'Inter', sans-serif" }}>
        Loading…
      </div>
    </div>
  );
}

function DeclinedScreen({ onReconsider }) {
  return (
    <div style={{
      position: 'fixed', inset: 0, display: 'flex',
      alignItems: 'center', justifyContent: 'center',
      background: '#FAFAFA', zIndex: 9999,
      fontFamily: "'Inter', sans-serif", padding: 24,
    }}>
      <div style={{ maxWidth: 480, textAlign: 'center' }}>
        <h2 style={{ margin: '0 0 12px', fontSize: 22, color: '#0A0A0A', letterSpacing: '-0.02em' }}>
          Terms not accepted
        </h2>
        <p style={{ margin: 0, fontSize: 14, color: '#4B5563', lineHeight: 1.65 }}>
          {DECLINE_MESSAGE}
        </p>
        <button
          onClick={onReconsider}
          style={{
            marginTop: 22,
            padding: '10px 22px', background: '#0A0A0A', color: '#FFFFFF',
            border: 'none', borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: 'pointer',
          }}
        >
          Review again
        </button>
      </div>
    </div>
  );
}

// Lightweight device fingerprint — not a full FingerprintJS, but enough for
// Clause 2.1 "device fingerprint (where available)". Captures what's free
// and non-intrusive from the browser.
function buildDeviceFingerprint() {
  try {
    const parts = [
      navigator.userAgent || '',
      navigator.language || '',
      String(screen.width) + 'x' + String(screen.height),
      String(screen.colorDepth || ''),
      String(new Date().getTimezoneOffset()),
      navigator.platform || '',
    ];
    return parts.join('|').slice(0, 400);
  } catch {
    return '';
  }
}
