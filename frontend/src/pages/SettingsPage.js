import React, { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Loader2, Check, Shield, User as UserIcon, Zap, Activity, ExternalLink, AlertCircle, Trash2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { GoogleDriveStatusChip } from '../components/GoogleDriveConnect';

const API = process.env.NODE_ENV === 'development' ? '/api' : '/api';

/**
 * Settings Page — account, usage, integrations, security, deployment info.
 */
export default function SettingsPage() {
  const { user, getToken } = useAuth();
  const [usage, setUsage] = useState(null);
  const [deployment, setDeployment] = useState(null);
  const [auditTrail, setAuditTrail] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchAll = useCallback(async () => {
    try {
      let token = '';

      try { token = await getToken() || token; } catch { /**/ }
      try { token = await getToken() || token; } catch {}

      const [usageRes, depRes, auditRes] = await Promise.all([
        fetch(`${API}/user/usage`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${API}/deployment/info`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${API}/user/audit-trail?limit=25`, { headers: { Authorization: `Bearer ${token}` } }),
      ]);
      if (usageRes.ok) setUsage(await usageRes.json());
      if (depRes.ok) setDeployment(await depRes.json());
      if (auditRes.ok) {
        const d = await auditRes.json();
        setAuditTrail(d.events || []);
      }
    } catch (e) {
      console.warn('Settings load failed:', e);
    }
    setLoading(false);
  }, [getToken]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  return (
    <div style={{ padding: '48px 40px 80px', maxWidth: 920, margin: '0 auto', background: '#FFFFFF', minHeight: '100%' }}>
      {/* Header */}
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: 28, fontWeight: 700, color: '#0A0A0A', margin: 0, letterSpacing: '-0.02em' }}>Settings</h1>
        <p style={{ fontSize: 13, color: '#888', margin: '4px 0 0', fontWeight: 500 }}>Account, usage, integrations, and security</p>
      </div>

      {loading ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#888', fontSize: 13 }}>
          <Loader2 style={{ width: 14, height: 14, animation: 'spin 0.8s linear infinite' }} /> Loading...
        </div>
      ) : (
        <>
          {/* ACCOUNT SECTION */}
          <Section title="Account" icon={UserIcon}>
            <Row label="Email" value={user?.email || 'Not signed in'} />
            <Row label="Name" value={user?.name || user?.displayName || '—'} />
            <Row label="User ID" value={usage?.user_id?.slice(0, 20) + '...' || '—'} mono />
            <Row label="Tier" value={<Badge>{usage?.tier?.toUpperCase() || 'FREE'}</Badge>} />
          </Section>

          {/* USAGE SECTION */}
          <Section title="Daily Usage" icon={Activity}>
            {usage?.usage ? (
              Object.entries(usage.usage).map(([key, val]) => (
                <UsageBar key={key} label={prettyLabel(key)} used={val.used} limit={val.limit} pct={val.pct} />
              ))
            ) : (
              <div style={{ color: '#999', fontSize: 12 }}>No usage data yet</div>
            )}
          </Section>

          {/* INTEGRATIONS SECTION */}
          <Section title="Integrations" icon={Zap}>
            <div style={{ padding: '12px 14px', border: '1px solid #EBEBEB', borderRadius: 10, background: '#FAFAFA' }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#0A0A0A', marginBottom: 8 }}>Google Drive</div>
              <div style={{ fontSize: 12, color: '#666', marginBottom: 10, lineHeight: 1.5 }}>
                Save generated Excel files as Google Sheets and Word docs as Google Docs directly to your own Drive.
              </div>
              <GoogleDriveStatusChip />
            </div>
          </Section>

          {/* DEPLOYMENT SECTION */}
          <Section title="Deployment" icon={Shield}>
            <Row label="Mode" value={deployment?.mode === 'dedicated' ? <Badge color="#D4AF37">Dedicated</Badge> : <Badge>Multi-tenant</Badge>} />
            <Row label="Instance" value={deployment?.firm_short === '_default' ? 'spectr.in (shared)' : deployment?.firm_short || '—'} />
            <Row label="Branding" value={deployment?.branding?.app_name || 'Spectr'} />
            {deployment?.features && (
              <div style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid #F0F0F0' }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: '#666', marginBottom: 8, letterSpacing: 0.2 }}>ENABLED FEATURES</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {Object.entries(deployment.features)
                    .filter(([_, v]) => v === true)
                    .map(([k]) => (
                      <span key={k} style={{ padding: '3px 9px', fontSize: 10.5, background: '#F5F5F5', borderRadius: 5, color: '#555', fontWeight: 500 }}>
                        {k.replace(/_/g, ' ')}
                      </span>
                    ))}
                </div>
              </div>
            )}
          </Section>

          {/* AUDIT TRAIL */}
          <Section title="Recent Activity" icon={Activity}>
            {auditTrail.length === 0 ? (
              <div style={{ color: '#999', fontSize: 12 }}>No recent activity</div>
            ) : (
              <div style={{ maxHeight: 320, overflowY: 'auto' }}>
                {auditTrail.map((e, i) => (
                  <div key={i} style={{ padding: '7px 0', borderBottom: i < auditTrail.length - 1 ? '1px solid #F5F5F5' : 'none', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
                    <div style={{ minWidth: 0, flex: 1 }}>
                      <div style={{ fontSize: 12, fontWeight: 500, color: '#0A0A0A' }}>{e.action}</div>
                      {e.resource_type && <div style={{ fontSize: 10.5, color: '#888', marginTop: 1 }}>{e.resource_type}</div>}
                    </div>
                    <div style={{ fontSize: 10.5, color: '#AAA', whiteSpace: 'nowrap' }}>{relTime(e.timestamp)}</div>
                  </div>
                ))}
              </div>
            )}
          </Section>

          {/* SECURITY */}
          <Section title="Security & Privacy" icon={Shield}>
            <Row label="Data encryption at rest" value={<Badge color="#10B981">AES-256</Badge>} />
            <Row label="OAuth tokens" value={<Badge color="#10B981">Fernet encrypted</Badge>} />
            <Row label="Audit logging" value={<Badge color="#10B981">Enabled</Badge>} />
            <Row label="Rate limiting" value={<Badge color="#10B981">Per-user daily</Badge>} />
            <div style={{ marginTop: 14, padding: '10px 12px', background: '#FFF9E6', border: '1px solid #FFE9A8', borderRadius: 8, display: 'flex', gap: 8, alignItems: 'flex-start' }}>
              <AlertCircle style={{ width: 14, height: 14, color: '#B88217', flexShrink: 0, marginTop: 1 }} />
              <div style={{ fontSize: 11.5, color: '#8A6816', lineHeight: 1.5 }}>
                All analysis is AI-generated. Citations are verified against IndianKanoon live API and MongoDB statute DB. Always independently verify before filing or client delivery.
              </div>
            </div>
          </Section>
        </>
      )}
    </div>
  );
}

// --- Sub-components ---

function Section({ title, icon: Icon, children }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      style={{ marginBottom: 28 }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
        <Icon style={{ width: 14, height: 14, color: '#0A0A0A', strokeWidth: 2 }} />
        <h2 style={{ fontSize: 15, fontWeight: 700, color: '#0A0A0A', margin: 0, letterSpacing: '-0.01em' }}>{title}</h2>
      </div>
      <div style={{ padding: '14px 16px', border: '1px solid #EDEDED', borderRadius: 12, background: '#FFFFFF' }}>
        {children}
      </div>
    </motion.div>
  );
}

function Row({ label, value, mono }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '7px 0', borderBottom: '1px solid #F7F7F7', fontSize: 12.5 }}>
      <span style={{ color: '#666', fontWeight: 500 }}>{label}</span>
      <span style={{ color: '#0A0A0A', fontWeight: 500, fontFamily: mono ? 'monospace' : 'inherit' }}>{value}</span>
    </div>
  );
}

function Badge({ children, color = '#6B6B6B' }) {
  return (
    <span style={{ padding: '2px 8px', fontSize: 10.5, fontWeight: 600, color: '#fff', background: color, borderRadius: 5, letterSpacing: 0.2 }}>
      {children}
    </span>
  );
}

function UsageBar({ label, used, limit, pct }) {
  const color = pct > 80 ? '#EF4444' : pct > 50 ? '#F59E0B' : '#10B981';
  return (
    <div style={{ padding: '8px 0', borderBottom: '1px solid #F7F7F7' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 5 }}>
        <span style={{ color: '#555', fontWeight: 500 }}>{label}</span>
        <span style={{ color: '#888', fontWeight: 500 }}>{used} / {limit}</span>
      </div>
      <div style={{ height: 4, background: '#F0F0F0', borderRadius: 2, overflow: 'hidden' }}>
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${Math.min(100, pct)}%` }}
          transition={{ duration: 0.5 }}
          style={{ height: '100%', background: color }}
        />
      </div>
    </div>
  );
}

function prettyLabel(key) {
  return key
    .replace(/^max_/, '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase());
}

function relTime(iso) {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    const mins = (Date.now() - d.getTime()) / 60000;
    if (mins < 1) return 'just now';
    if (mins < 60) return `${Math.round(mins)}m ago`;
    if (mins < 1440) return `${Math.round(mins / 60)}h ago`;
    return `${Math.round(mins / 1440)}d ago`;
  } catch {
    return '—';
  }
}
