import React, { useState, useEffect } from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import CommandPalette from '../components/CommandPalette';
import {
  Scale, MessageSquare, FolderOpen, Workflow, BookOpen,
  History, LogOut, ChevronDown, Search, User, FileSpreadsheet,
  Timer, Calculator, Shield, Briefcase, Zap
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

export default function DashboardLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);

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
    <div style={{ height: '100vh', display: 'flex', background: '#FAFBFC', overflow: 'hidden', fontFamily: 'Inter, sans-serif' }} data-testid="dashboard-layout">
      {/* Sidebar */}
      <aside
        className="app-sidebar"
        style={{
          width: 232,
          display: 'flex',
          flexDirection: 'column',
          flexShrink: 0,
        }}
        data-testid="sidebar"
      >
        {/* Logo */}
        <div style={{
          height: 56,
          padding: '0 16px',
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          borderBottom: '1px solid #E2E8F0',
        }}>
          <div style={{
            width: 30, height: 30,
            background: '#0A0A0A',
            borderRadius: 8,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <Scale style={{ width: 15, height: 15, color: '#fff' }} />
          </div>
          <span style={{ fontSize: 16, fontWeight: 700, color: '#0A0A0A', letterSpacing: '-0.02em' }}>Associate</span>
        </div>

        {/* Search */}
        <div style={{ padding: '12px 12px 8px' }}>
          <button
            onClick={() => setCommandPaletteOpen(true)}
            style={{
              width: '100%',
              display: 'flex', alignItems: 'center', gap: 7,
              padding: '6px 10px',
              background: '#F8FAFC',
              border: '1px solid #E2E8F0',
              borderRadius: 8,
              color: '#94A3B8',
              fontSize: 12.5,
              cursor: 'pointer',
              transition: 'all 0.15s',
            }}
            onMouseEnter={e => e.currentTarget.style.background = '#F1F5F9'}
            onMouseLeave={e => e.currentTarget.style.background = '#F8FAFC'}
            data-testid="cmd-k-trigger"
          >
            <Search style={{ width: 13, height: 13 }} />
            <span style={{ flex: 1, textAlign: 'left' }}>Search...</span>
            <kbd style={{
              fontSize: 10, fontFamily: 'IBM Plex Mono, monospace',
              background: '#fff', border: '1px solid #E2E8F0', borderRadius: 4, padding: '1px 5px', color: '#94A3B8',
            }}>⌘K</kbd>
          </button>
        </div>

        {/* Nav */}
        <nav style={{ flex: 1, padding: '4px 10px', overflowY: 'auto' }}>
          <div style={{ fontSize: 10, fontWeight: 600, color: '#94A3B8', letterSpacing: '0.09em', padding: '8px 4px 4px', textTransform: 'uppercase' }}>
            Workspace
          </div>
          {NAV_ITEMS.map(item => (
            <NavLink
              key={item.path}
              to={item.path}
              data-testid={`nav-${item.label.toLowerCase()}`}
              style={({ isActive }) => ({
                display: 'flex', alignItems: 'center', gap: 9,
                padding: '7px 10px',
                borderRadius: 8,
                fontSize: 13.5, fontWeight: 500,
                color: isActive ? '#0A0A0A' : '#4A4A4A',
                background: isActive ? '#F1F5F9' : 'transparent',
                border: `1px solid ${isActive ? '#E2E8F0' : 'transparent'}`,
                textDecoration: 'none',
                marginBottom: 1,
                transition: 'all 0.15s',
              })}
            >
              <item.icon style={{ width: 14, height: 14 }} />
              {item.label}
            </NavLink>
          ))}
        </nav>

        {/* Live status */}
        <div style={{
          padding: '8px 14px',
          display: 'flex', alignItems: 'center', gap: 6,
          borderTop: '1px solid #F1F5F9',
          background: '#FAFBFC',
        }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#10B981', display: 'inline-block', boxShadow: '0 0 6px rgba(16,185,129,0.5)' }} />
          <span style={{ fontSize: 11, color: '#64748B', fontWeight: 500 }}>Council Active</span>
          <Zap style={{ width: 10, height: 10, color: '#94A3B8', marginLeft: 'auto' }} />
        </div>

        {/* User */}
        <div style={{ borderTop: '1px solid #E2E8F0', padding: 10, position: 'relative' }}>
          <div
            style={{
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '7px 8px', borderRadius: 8, cursor: 'pointer', transition: 'background 0.15s',
            }}
            onMouseEnter={e => e.currentTarget.style.background = '#F1F5F9'}
            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
            onClick={() => setShowUserMenu(!showUserMenu)}
            data-testid="user-menu-trigger"
          >
            {user?.picture ? (
              <img src={user.picture} alt="" style={{ width: 26, height: 26, borderRadius: '50%', border: '1px solid #E2E8F0' }} />
            ) : (
              <div style={{ width: 26, height: 26, background: '#0A0A0A', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <User style={{ width: 12, height: 12, color: '#fff' }} />
              </div>
            )}
            <div style={{ flex: 1, minWidth: 0 }}>
              <p style={{ fontSize: 12.5, fontWeight: 600, color: '#0A0A0A', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{user?.name || 'User'}</p>
              <p style={{ fontSize: 10, color: '#94A3B8', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{user?.email || ''}</p>
            </div>
            <ChevronDown style={{ width: 11, height: 11, color: '#94A3B8' }} />
          </div>
          {showUserMenu && (
            <div style={{
              position: 'absolute', bottom: 58, left: 10, right: 10,
              background: '#fff', border: '1px solid #E2E8F0', borderRadius: 10, zIndex: 50,
              boxShadow: '0 8px 32px rgba(0,0,0,0.08)',
            }}>
              <button onClick={handleLogout}
                style={{
                  width: '100%', display: 'flex', alignItems: 'center', gap: 8,
                  padding: '10px 14px', fontSize: 13, color: '#DC2626',
                  background: 'none', border: 'none', cursor: 'pointer', borderRadius: 10,
                }}
                onMouseEnter={e => e.currentTarget.style.background = '#FEF2F2'}
                onMouseLeave={e => e.currentTarget.style.background = 'none'}
                data-testid="logout-btn">
                <LogOut style={{ width: 13, height: 13 }} />
                Sign Out
              </button>
            </div>
          )}
        </div>
      </aside>

      {/* Main */}
      <main style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden', background: '#FFFFFF' }}>
        <Outlet />
      </main>

      <CommandPalette isOpen={commandPaletteOpen} onClose={() => setCommandPaletteOpen(false)} />
    </div>
  );
}
