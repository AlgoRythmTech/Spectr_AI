import React, { useState, useEffect, useRef } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '../context/AuthContext';
import CommandPalette from '../components/CommandPalette';
import { GoogleDriveStatusChip } from '../components/GoogleDriveConnect';
import PreviousChatsSidebar from '../components/PreviousChatsSidebar';
import {
  MessageSquare, FolderOpen, Workflow, BookOpen,
  History, LogOut, Search, User,
  Plus, Scale, ChevronDown, Menu, BarChart3,
  Settings, HelpCircle, Gavel, Calendar,
  Briefcase,
} from 'lucide-react';

const NAV_ITEMS = [
  { path: '/app/assistant', icon: MessageSquare, label: 'Assistant' },
  { path: '/app/caselaw', icon: Scale, label: 'Legal Research' },
  { path: '/app/vault', icon: FolderOpen, label: 'Documents' },
  { path: '/app/reconciler', icon: BarChart3, label: 'Reconciler' },
  { path: '/app/workflows', icon: Workflow, label: 'Workflows' },
  { path: '/app/court-tracker', icon: Gavel, label: 'Court Tracker' },
  { path: '/app/portfolio', icon: Briefcase, label: 'Portfolio' },
  { path: '/app/history', icon: History, label: 'History' },
  { path: '/app/library', icon: BookOpen, label: 'Knowledge Base' },
];


const API = process.env.NODE_ENV === 'development' ? '/api' : '/api';

export default function DashboardLayout() {
  const { user, logout, getToken } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const userMenuRef = useRef(null);

  // Sidebar collapse state — persisted per browser so user's choice sticks across reloads
  const [leftCollapsed, setLeftCollapsed] = useState(() => {
    try { return localStorage.getItem('spectr_left_collapsed') === '1'; } catch { return false; }
  });
  const [rightCollapsed, setRightCollapsed] = useState(() => {
    try { return localStorage.getItem('spectr_right_collapsed') === '1'; } catch { return false; }
  });
  const toggleLeft = () => setLeftCollapsed(v => { try { localStorage.setItem('spectr_left_collapsed', !v ? '1' : '0'); } catch {} return !v; });
  const toggleRight = () => setRightCollapsed(v => { try { localStorage.setItem('spectr_right_collapsed', !v ? '1' : '0'); } catch {} return !v; });

  // T&C acceptance is gated at the route level in App.js via TOSAcceptanceGate
  // wrapping ProtectedRoute — by the time this layout mounts, the user has
  // already satisfied that gate, so no modal state is needed here.

  useEffect(() => { setShowUserMenu(false); }, [location.pathname]);

  // Inject <meta name="robots" content="noindex, nofollow"> while the user
  // is inside the private app. Crawlers should never surface the dashboard
  // in search results (robots.txt also Disallows /app/, this is belt-and-braces).
  useEffect(() => {
    const tag = document.createElement('meta');
    tag.setAttribute('name', 'robots');
    tag.setAttribute('content', 'noindex, nofollow');
    document.head.appendChild(tag);
    return () => { try { document.head.removeChild(tag); } catch {} };
  }, []);

  useEffect(() => {
    const down = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') { e.preventDefault(); setCommandPaletteOpen(p => !p); }
      // ⌘\ toggles the left rail, ⌘. toggles the right rail — matches the hints in ?
      if ((e.ctrlKey || e.metaKey) && e.key === '\\') { e.preventDefault(); toggleLeft(); }
      if ((e.ctrlKey || e.metaKey) && e.key === '.')  { e.preventDefault(); toggleRight(); }
    };
    window.addEventListener('keydown', down);
    return () => window.removeEventListener('keydown', down);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const click = (e) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target)) setShowUserMenu(false);
    };
    document.addEventListener('mousedown', click);
    return () => document.removeEventListener('mousedown', click);
  }, []);

  const handleLogout = async () => { await logout(); navigate('/'); };

  return (
    <div style={{
      height: '100vh', display: 'flex',
      fontFamily: "'Inter', sans-serif",
      // Subtle radial gradient gives the glass sidebars something warm to blur
      background: 'radial-gradient(ellipse 120% 80% at 50% 0%, rgba(255,240,220,0.35) 0%, rgba(240,245,255,0.25) 40%, #FFFFFF 85%)',
      overflow: 'hidden',
    }}>

      <style>{`
        @keyframes menuUp {
          from { opacity:0; transform:translateY(8px) scale(0.96); }
          to   { opacity:1; transform:translateY(0) scale(1); }
        }
        @keyframes spin { to { transform:rotate(360deg); } }

        /* ── Nav items ── */
        .s-nav-item {
          width: 100%; display: flex; align-items: center; gap: 10px;
          padding: 7px 11px; margin-bottom: 1px;
          font-size: 13px; font-weight: 450;
          color: #999; background: transparent;
          border: none; border-radius: 8px; cursor: pointer;
          text-align: left; font-family: 'Inter', sans-serif;
          transition: background 0.12s, color 0.12s, box-shadow 0.12s; position: relative;
        }
        .s-nav-item:hover { background: rgba(0,0,0,0.03) !important; color: #555 !important; }
        .s-nav-item.active {
          background: #FFFFFF !important;
          color: #0A0A0A !important; font-weight: 550;
          box-shadow: 0 1px 2px rgba(0,0,0,0.04);
        }
        .s-nav-item.active .s-dot { opacity: 1 !important; }

        /* ── New conv button ── */
        .s-new-btn {
          width: 28px; height: 28px; display: flex; align-items: center; justify-content: center;
          padding: 0;
          background: #FFFFFF;
          border: 1px solid rgba(0,0,0,0.06);
          color: #0A0A0A;
          border-radius: 8px; cursor: pointer;
          font-family: 'Inter', sans-serif;
          transition: all 0.15s;
          box-shadow: 0 1px 2px rgba(0,0,0,0.03);
        }
        .s-new-btn:hover { background: #F9F9F9; border-color: rgba(0,0,0,0.1); }

        /* ── Search bar ── */
        .s-search-btn {
          width: 100%; display: flex; align-items: center; gap: 8px;
          padding: 0 12px; height: 36px;
          background: #FFFFFF;
          border: 1px solid rgba(0,0,0,0.06);
          border-radius: 9px; font-size: 12.5px; color: #AAAAAA;
          cursor: pointer; font-family: 'Inter', sans-serif;
          transition: all 0.15s;
          box-shadow: 0 1px 2px rgba(0,0,0,0.03);
        }
        .s-search-btn:hover { border-color: rgba(0,0,0,0.1); color: #666; }

        /* ── User button ── */
        .s-user-btn:hover { background: #F5F5F5 !important; }

        /* ── Scrollbar ── */
        .s-scroll::-webkit-scrollbar { width: 3px; }
        .s-scroll::-webkit-scrollbar-track { background: transparent; }
        .s-scroll::-webkit-scrollbar-thumb { background: #E5E5E5; border-radius: 3px; }
        .s-scroll::-webkit-scrollbar-thumb:hover { background: #CCC; }

        /* ── Right rail collapsed mode — icons only, labels hidden ── */
        .right-rail.collapsed .s-nav-item { justify-content: center; padding: 8px 0; }
        .right-rail.collapsed .s-nav-item > span:not(.s-dot) { display: none; }
        .right-rail.collapsed .s-search-btn { justify-content: center; padding: 0; height: 32px; width: 32px; margin: 0 auto; }
        .right-rail.collapsed .s-search-btn > span,
        .right-rail.collapsed .s-search-btn kbd { display: none; }
        .right-rail.collapsed .rr-logo-text,
        .right-rail.collapsed .rr-label-only,
        .right-rail.collapsed .rr-user-text { display: none; }
        .right-rail.collapsed .rr-top-row { flex-direction: column; gap: 8px; }
        .right-rail.collapsed .rr-user-row { justify-content: center; }
      `}</style>

      {/* ─── LEFT RAIL: PREVIOUS CHATS (order: 0 applied inside the component's aside) ─── */}
      <PreviousChatsSidebar collapsed={leftCollapsed} onToggle={toggleLeft} />

      {/* ─── RIGHT RAIL: OPTIONS / NAV — Apple liquid glass (order: 2) ─── */}
      <aside className={`right-rail${rightCollapsed ? ' collapsed' : ''}`} style={{
        order: 2,
        width: rightCollapsed ? 56 : 252,
        flexShrink: 0,
        height: '100%', display: 'flex', flexDirection: 'column',
        position: 'relative',
        // Apple liquid-glass finish, mirrored on the opposite edge
        background: 'linear-gradient(180deg, rgba(255,255,255,0.72) 0%, rgba(250,250,250,0.62) 100%)',
        backdropFilter: 'blur(40px) saturate(180%)',
        WebkitBackdropFilter: 'blur(40px) saturate(180%)',
        borderLeft: '1px solid rgba(255,255,255,0.6)',
        boxShadow: 'inset 1px 0 0 rgba(0,0,0,0.04), inset -1px 0 0 rgba(255,255,255,0.8), -4px 0 24px -12px rgba(0,0,0,0.08)',
        overflow: 'hidden',
        transition: 'width 0.28s cubic-bezier(0.22, 1, 0.36, 1)',
      }}>
        {/* Header row — hamburger + logo, inline */}
        <div style={{
          padding: '18px 12px 16px',
          flexShrink: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: rightCollapsed ? 'center' : 'flex-start',
          gap: 10,
        }}>
          {/* Hamburger — 3 lines, click to collapse/expand */}
          <button
            onClick={toggleRight}
            title={rightCollapsed ? 'Expand panel' : 'Collapse panel'}
            aria-label={rightCollapsed ? 'Expand panel' : 'Collapse panel'}
            style={{
              width: 34, height: 34, borderRadius: 9,
              background: 'transparent',
              border: 'none',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'pointer', padding: 0, flexShrink: 0,
              transition: 'background 0.15s',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(0,0,0,0.06)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
          >
            <Menu style={{ width: 19, height: 19, color: '#0A0A0A', strokeWidth: 2 }} />
          </button>
          {/* Logo — hidden when collapsed */}
          {!rightCollapsed && (
            <span
              onClick={() => navigate('/app/assistant')}
              style={{
                fontFamily: "'Inter', sans-serif",
                fontSize: 24, fontWeight: 500, letterSpacing: '-0.05em',
                background: 'linear-gradient(to bottom right, #0A0A0A 40%, rgba(10,10,10,0.45))',
                WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
                backgroundClip: 'text',
                cursor: 'pointer', userSelect: 'none',
                display: 'inline-block',
              }}
            >
              Spectr
            </span>
          )}
        </div>

        {/* Top row: New chat + Search (stacks vertically when collapsed) */}
        <div className="rr-top-row" style={{ padding: '0 10px 10px', flexShrink: 0, display: 'flex', alignItems: 'center', gap: 6 }}>
          <button className="s-new-btn" onClick={() => navigate('/app/assistant')} title="New chat">
            <Plus style={{ width: 13, height: 13, strokeWidth: 2.2, flexShrink: 0 }} />
          </button>
          <button className="s-search-btn" onClick={() => setCommandPaletteOpen(true)} style={{ flex: 1 }}>
            <Search style={{ width: 12, height: 12, flexShrink: 0, color: '#999' }} />
            <span style={{ flex: 1, textAlign: 'left', color: '#999', fontWeight: 500 }}>Search</span>
            <kbd style={{
              fontSize: 9.5, background: 'transparent', border: '1px solid rgba(0,0,0,0.08)',
              borderRadius: 4, padding: '1px 5px', color: '#AAA',
              fontFamily: 'inherit',
            }}>⌘K</kbd>
          </button>
        </div>

        {/* Navigation */}
        <nav style={{ padding: '0 10px 0', flexShrink: 0 }}>
          {NAV_ITEMS.map(item => {
            const isActive = location.pathname === item.path ||
              (item.path === '/app/assistant' && location.pathname === '/app');
            return (
              <button
                key={item.path}
                className={`s-nav-item${isActive ? ' active' : ''}`}
                onClick={() => navigate(item.path)}
              >
                <item.icon style={{
                  width: 15, height: 15,
                  strokeWidth: isActive ? 2 : 1.6,
                  flexShrink: 0,
                  color: isActive ? '#0A0A0A' : '#A8A8A8',
                }} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Google Drive connection */}
        <div style={{ padding: '0 10px', marginTop: 'auto', flexShrink: 0, marginBottom: 6 }}>
          <GoogleDriveStatusChip />
        </div>

        {/* Bottom nav */}
        <div style={{ padding: '0 10px', flexShrink: 0 }}>
          {[
            { icon: Settings, label: 'Settings', path: '/app/settings' },
            { icon: HelpCircle, label: 'Help', action: () => window.open('https://spectr.in/support', '_blank') },
          ].map(item => {
            const active = item.path && location.pathname === item.path;
            return (
              <button
                key={item.label}
                className={`s-nav-item${active ? ' active' : ''}`}
                onClick={() => item.path ? navigate(item.path) : item.action?.()}
              >
                <item.icon style={{ width: 15, height: 15, strokeWidth: active ? 2 : 1.6, flexShrink: 0, color: active ? '#0A0A0A' : '#A8A8A8' }} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </div>

        {/* Divider */}
        <div style={{ height: 1, background: 'rgba(0,0,0,0.04)', margin: '8px 12px 0', flexShrink: 0 }} />

        {/* User section */}
        <div style={{ padding: '8px 8px 12px', flexShrink: 0 }}>
          <div ref={userMenuRef} style={{ position: 'relative' }}>
            <button
              className="s-user-btn rr-user-row"
              onClick={() => setShowUserMenu(!showUserMenu)}
              style={{
                width: '100%', display: 'flex', alignItems: 'center', gap: 9,
                padding: '8px 10px', background: 'none', border: 'none',
                borderRadius: 9, cursor: 'pointer', transition: 'background 0.12s',
              }}
            >
              <div style={{
                width: 26, height: 26, borderRadius: '50%',
                overflow: 'hidden', flexShrink: 0,
                border: '1px solid rgba(0,0,0,0.08)',
                background: '#EDEDED',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }} title={user?.email || ''}>
                {user?.picture
                  ? <img src={user.picture} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                  : <User style={{ width: 12, height: 12, color: '#666' }} />
                }
              </div>
              <div className="rr-user-text" style={{ flex: 1, minWidth: 0, textAlign: 'left' }}>
                <div style={{
                  fontFamily: "'Inter', sans-serif",
                  fontSize: 12.5, fontWeight: 550, color: '#0A0A0A',
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  letterSpacing: '-0.005em',
                }}>
                  {user?.name || 'Account'}
                </div>
              </div>
              <ChevronDown className="rr-user-text" style={{
                width: 11, height: 11, color: '#444', flexShrink: 0,
                transform: showUserMenu ? 'rotate(180deg)' : 'none',
                transition: 'transform 0.15s',
              }} />
            </button>

            {showUserMenu && (
              <div style={{
                position: 'absolute', bottom: 'calc(100% + 6px)', left: 0, right: 0,
                background: '#FFFFFF', border: '1px solid #E5E5E5', borderRadius: 10,
                boxShadow: '0 8px 32px rgba(0,0,0,0.08)', zIndex: 50, padding: 4,
                animation: 'menuUp 0.16s cubic-bezier(0.16,1,0.3,1)',
              }}>
                <button
                  onClick={handleLogout}
                  style={{
                    width: '100%', display: 'flex', alignItems: 'center', gap: 8,
                    padding: '8px 10px', fontSize: 13, color: '#666',
                    background: 'none', border: 'none', cursor: 'pointer',
                    borderRadius: 7, fontFamily: "'Inter', sans-serif",
                    transition: 'background 0.1s, color 0.1s',
                  }}
                  onMouseEnter={e => { e.currentTarget.style.background = '#F5F5F5'; e.currentTarget.style.color = '#0A0A0A'; }}
                  onMouseLeave={e => { e.currentTarget.style.background = 'none'; e.currentTarget.style.color = '#666'; }}
                >
                  <LogOut style={{ width: 13, height: 13 }} />
                  Sign out
                </button>
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* ─── MAIN CONTENT (order: 1 — middle) ─── */}
      <main style={{
        order: 1,
        flex: 1, minWidth: 0,
        display: 'flex', flexDirection: 'column',
        overflow: 'hidden', background: 'transparent',
        position: 'relative',
      }}>
        {/* Page transitions — each route fades + gently scales in */}
        <AnimatePresence mode="wait">
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, y: 6, scale: 0.995, filter: 'blur(4px)' }}
            animate={{ opacity: 1, y: 0, scale: 1, filter: 'blur(0px)' }}
            exit={{ opacity: 0, y: -4, scale: 1.002, filter: 'blur(4px)' }}
            transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
            style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}
          >
            <Outlet />
          </motion.div>
        </AnimatePresence>
      </main>

      <CommandPalette isOpen={commandPaletteOpen} onClose={() => setCommandPaletteOpen(false)} />
    </div>
  );
}
