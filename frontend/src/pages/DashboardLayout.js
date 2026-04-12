import React, { useState, useEffect } from 'react';
import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import CommandPalette from '../components/CommandPalette';
import {
  MessageSquare, FolderOpen, Workflow, BookOpen,
  History, LogOut, ChevronDown, Search, User, FileSpreadsheet,
  Briefcase, Plus, Scale
} from 'lucide-react';

const NAV_ITEMS = [
  { path: '/app/assistant', icon: MessageSquare, label: 'Assistant' },
  { path: '/app/caselaw', icon: Scale, label: 'Case Finder' },
  { path: '/app/court-tracker', icon: Briefcase, label: 'Court Tracker' },
  { path: '/app/vault', icon: FolderOpen, label: 'Vault' },
  { path: '/app/workflows', icon: Workflow, label: 'Workflows' },
  { path: '/app/library', icon: BookOpen, label: 'Library' },
  { path: '/app/history', icon: History, label: 'History' },
  { path: '/app/reconciler', icon: FileSpreadsheet, label: 'GSTR-2B' },
];

const display = "'Plus Jakarta Sans', 'Inter', sans-serif";

export default function DashboardLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);

  useEffect(() => { setShowUserMenu(false); }, [location.pathname]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setCommandPaletteOpen(prev => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  return (
    <div style={{
      height: '100vh', display: 'flex', overflow: 'hidden',
      fontFamily: "'Plus Jakarta Sans', 'Inter', sans-serif", background: '#FAFAFA',
    }}>
      <aside style={{
        width: 252, display: 'flex', flexDirection: 'column', flexShrink: 0,
        background: '#FAFAFA', padding: '16px 12px',
        borderRight: '1px solid rgba(0,0,0,0.04)',
      }}>
        {/* Serif wordmark + new chat */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '4px 8px 20px',
        }}>
          <span style={{
            fontFamily: display, fontSize: 18, fontWeight: 700,
            color: '#0A0A0A', letterSpacing: '-0.03em',
          }}>
            Associate
          </span>
          <button
            onClick={() => navigate('/app/assistant')}
            title="New chat"
            style={{
              width: 28, height: 28, display: 'flex', alignItems: 'center', justifyContent: 'center',
              background: '#fff', border: '1px solid rgba(0,0,0,0.08)', borderRadius: 8,
              cursor: 'pointer', color: '#999', transition: 'all 0.15s',
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(0,0,0,0.15)'; e.currentTarget.style.color = '#555'; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(0,0,0,0.08)'; e.currentTarget.style.color = '#999'; }}
          >
            <Plus style={{ width: 14, height: 14 }} />
          </button>
        </div>

        {/* Search */}
        <button
          onClick={() => setCommandPaletteOpen(true)}
          style={{
            width: '100%', height: 36, display: 'flex', alignItems: 'center', gap: 8,
            padding: '0 12px', background: '#fff',
            border: '1px solid rgba(0,0,0,0.06)',
            borderRadius: 9, color: '#B0B0B0', fontSize: 13, cursor: 'pointer',
            transition: 'border-color 0.15s', fontFamily: "'Inter', sans-serif",
            marginBottom: 16, boxSizing: 'border-box',
          }}
          onMouseEnter={e => e.currentTarget.style.borderColor = 'rgba(0,0,0,0.12)'}
          onMouseLeave={e => e.currentTarget.style.borderColor = 'rgba(0,0,0,0.06)'}
        >
          <Search style={{ width: 14, height: 14, flexShrink: 0 }} />
          <span style={{ flex: 1, textAlign: 'left' }}>Search...</span>
          <kbd style={{
            fontSize: 10, fontFamily: "'Inter', sans-serif",
            background: '#F5F5F5', border: '1px solid rgba(0,0,0,0.05)',
            borderRadius: 4, padding: '2px 5px', color: '#C0C0C0',
          }}>⌘K</kbd>
        </button>

        {/* Nav */}
        <nav style={{ flex: 1, overflowY: 'auto' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {NAV_ITEMS.map(item => {
              const isActive = location.pathname === item.path ||
                (item.path === '/app/assistant' && location.pathname === '/app');
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 10,
                    padding: '8px 12px', borderRadius: 8,
                    fontSize: 13, fontWeight: isActive ? 550 : 450,
                    color: isActive ? '#0A0A0A' : '#999',
                    background: isActive ? '#fff' : 'transparent',
                    boxShadow: isActive ? '0 1px 2px rgba(0,0,0,0.04)' : 'none',
                    textDecoration: 'none',
                    transition: 'all 0.15s cubic-bezier(0.16, 1, 0.3, 1)',
                    letterSpacing: '-0.01em',
                  }}
                  onMouseEnter={e => {
                    if (!isActive) { e.currentTarget.style.background = 'rgba(0,0,0,0.025)'; e.currentTarget.style.color = '#555'; }
                  }}
                  onMouseLeave={e => {
                    if (!isActive) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#999'; }
                  }}
                >
                  <item.icon style={{ width: 15, height: 15, strokeWidth: isActive ? 1.8 : 1.6 }} />
                  {item.label}
                </NavLink>
              );
            })}
          </div>
        </nav>

        {/* User */}
        <div style={{ padding: '8px 0 0', position: 'relative' }}>
          <div
            onClick={() => setShowUserMenu(!showUserMenu)}
            title={user?.email || ''}
            style={{
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '8px 12px', borderRadius: 8, cursor: 'pointer',
              transition: 'background 0.15s',
            }}
            onMouseEnter={e => e.currentTarget.style.background = 'rgba(0,0,0,0.025)'}
            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
          >
            {user?.picture ? (
              <img src={user.picture} alt="" style={{ width: 26, height: 26, borderRadius: '50%' }} />
            ) : (
              <div style={{
                width: 26, height: 26, background: '#0A0A0A', borderRadius: '50%',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <User style={{ width: 12, height: 12, color: '#fff' }} />
              </div>
            )}
            <span style={{
              flex: 1, fontSize: 13, fontWeight: 550, color: '#0A0A0A',
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            }}>
              {user?.name || 'User'}
            </span>
            <ChevronDown style={{ width: 11, height: 11, color: '#CCC' }} />
          </div>

          {showUserMenu && (
            <div style={{
              position: 'absolute', bottom: 48, left: 0, right: 0,
              background: '#fff', border: '1px solid rgba(0,0,0,0.08)', borderRadius: 10,
              boxShadow: '0 8px 32px rgba(0,0,0,0.08)', zIndex: 50, padding: 4,
              animation: 'slideUp 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
            }}>
              {user?.email && (
                <div style={{ padding: '7px 12px', fontSize: 11, color: '#999' }}>{user.email}</div>
              )}
              <button onClick={handleLogout} style={{
                width: '100%', display: 'flex', alignItems: 'center', gap: 8,
                padding: '8px 12px', fontSize: 13, color: '#333',
                background: 'none', border: 'none', cursor: 'pointer', borderRadius: 6,
                transition: 'background 0.1s',
              }}
              onMouseEnter={e => e.currentTarget.style.background = '#F5F5F5'}
              onMouseLeave={e => e.currentTarget.style.background = 'none'}
              >
                <LogOut style={{ width: 13, height: 13 }} />
                Sign out
              </button>
            </div>
          )}
        </div>
      </aside>

      <main style={{
        flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column',
        overflow: 'hidden', background: '#fff',
      }}>
        <Outlet />
      </main>

      <CommandPalette isOpen={commandPaletteOpen} onClose={() => setCommandPaletteOpen(false)} />
    </div>
  );
}
