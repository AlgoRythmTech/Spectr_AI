import React from 'react';

/**
 * ErrorBoundary — catches React render errors anywhere in the tree and
 * shows a branded Spectr fallback instead of the white screen of death.
 *
 * Production-critical: without this, an exception thrown in any component
 * would crash the entire app and leave users staring at a blank page.
 *
 * In development, the actual error stack is shown for debugging.
 * In production, users get a friendly message + a "Reload" button + a
 * clipboard-copy of the error report to help support diagnose.
 */
export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, info: null, copied: false };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    this.setState({ info });
    // In production, this would POST to Sentry / Datadog / custom endpoint
    // For now, log to console.error (always — even when other logs are gated)
    console.error('[Spectr] ErrorBoundary caught:', error, info?.componentStack);
  }

  copyReport = () => {
    const { error, info } = this.state;
    const report = [
      `Spectr error report — ${new Date().toISOString()}`,
      `URL: ${typeof window !== 'undefined' ? window.location.href : '(SSR)'}`,
      `UA: ${typeof navigator !== 'undefined' ? navigator.userAgent : '(SSR)'}`,
      '',
      `Error: ${error?.name || ''}: ${error?.message || ''}`,
      '',
      'Stack:',
      error?.stack || '(no stack)',
      '',
      'Component stack:',
      info?.componentStack || '(no component stack)',
    ].join('\n');
    try {
      navigator.clipboard.writeText(report);
      this.setState({ copied: true });
      setTimeout(() => this.setState({ copied: false }), 2000);
    } catch { /* fallback: alert */ alert(report); }
  };

  reset = () => {
    this.setState({ hasError: false, error: null, info: null, copied: false });
  };

  render() {
    if (!this.state.hasError) return this.props.children;

    const isDev = process.env.NODE_ENV === 'development';
    const { error, info, copied } = this.state;

    return (
      <div style={{
        minHeight: '100vh', background: '#FFFFFF',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontFamily: "'Inter', sans-serif", padding: 24,
        color: '#0A0A0A',
      }}>
        <div style={{
          maxWidth: 560, width: '100%',
          background: '#FFFFFF',
          border: '1px solid rgba(0,0,0,0.06)',
          borderRadius: 20,
          boxShadow: '0 20px 60px rgba(0,0,0,0.08), 0 4px 16px rgba(0,0,0,0.04)',
          padding: '40px 40px 32px',
        }}>
          <div style={{
            width: 48, height: 48, borderRadius: 12,
            background: 'linear-gradient(135deg, #DC2626, #991B1B)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            marginBottom: 20,
            boxShadow: '0 6px 20px rgba(220,38,38,0.22)',
          }}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
          </div>

          <h1 style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: 28, fontWeight: 500, letterSpacing: '-0.045em',
            lineHeight: 1.1, margin: 0, marginBottom: 8,
            background: 'linear-gradient(to bottom right, #0A0A0A 40%, rgba(10,10,10,0.5))',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text',
          }}>
            Something broke.
          </h1>
          <p style={{
            margin: 0, marginBottom: 24,
            fontSize: 14, color: '#6B7280', lineHeight: 1.6, letterSpacing: '-0.005em',
          }}>
            Spectr hit an unexpected error. We&apos;ve logged it. Try reloading the page — if it keeps happening, copy the report below and send it to support.
          </p>

          {isDev && error && (
            <div style={{
              padding: '12px 14px', marginBottom: 20,
              background: '#FAFAFA', border: '1px solid #EBEBEB',
              borderRadius: 10,
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 11.5, color: '#B91C1C',
              maxHeight: 180, overflow: 'auto',
              whiteSpace: 'pre-wrap', wordBreak: 'break-word',
            }}>
              <div style={{ fontWeight: 600, marginBottom: 4 }}>{error.name || 'Error'}: {error.message}</div>
              {(error.stack || '').split('\n').slice(0, 6).map((line, i) => (
                <div key={i} style={{ color: '#6B7280', fontSize: 10.5 }}>{line}</div>
              ))}
            </div>
          )}

          <div style={{ display: 'flex', gap: 10 }}>
            <button
              onClick={() => { this.reset(); window.location.reload(); }}
              style={{
                flex: 1,
                padding: '12px 22px',
                background: 'linear-gradient(180deg, #1a1a1a 0%, #0a0a0a 100%)',
                color: '#fff',
                border: 'none', borderRadius: 12,
                fontFamily: "'Inter', sans-serif",
                fontSize: 14, fontWeight: 500, letterSpacing: '-0.01em',
                cursor: 'pointer',
                boxShadow: '0 8px 22px rgba(10,10,10,0.22), inset 0 1px 0 rgba(255,255,255,0.15)',
              }}
            >
              Reload Spectr
            </button>
            <button
              onClick={this.copyReport}
              style={{
                padding: '12px 20px',
                background: '#fff',
                color: '#555',
                border: '1px solid rgba(0,0,0,0.08)', borderRadius: 12,
                fontFamily: "'Inter', sans-serif",
                fontSize: 13, fontWeight: 500,
                cursor: 'pointer',
                letterSpacing: '-0.005em',
              }}
            >
              {copied ? 'Copied ✓' : 'Copy report'}
            </button>
          </div>

          <p style={{
            marginTop: 18, fontSize: 11, color: '#9CA3AF',
            textAlign: 'center', letterSpacing: '-0.005em',
          }}>
            Spectr &middot; AI Legal &amp; Accounting Platform
          </p>
        </div>
      </div>
    );
  }
}
