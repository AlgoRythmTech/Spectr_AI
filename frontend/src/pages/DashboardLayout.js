import React, { useState, useEffect } from 'react';
import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  Scale, MessageSquare, FolderOpen, Workflow, BookOpen,
  History, LogOut, ChevronDown, Search, User
} from 'lucide-react';

const NAV_ITEMS = [
  { path: '/app/assistant', icon: MessageSquare, label: 'Assistant' },
  { path: '/app/vault', icon: FolderOpen, label: 'Vault' },
  { path: '/app/workflows', icon: Workflow, label: 'Workflows' },
  { path: '/app/library', icon: BookOpen, label: 'Library' },
  { path: '/app/history', icon: History, label: 'History' },
];

export default function DashboardLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [showUserMenu, setShowUserMenu] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  return (
    <div className="h-screen flex bg-white" data-testid="dashboard-layout">
      {/* Sidebar */}
      <aside
        className="w-[240px] shrink-0 border-r border-[#E2E8F0] bg-[#F8FAFC] flex flex-col"
        data-testid="sidebar"
      >
        {/* Logo */}
        <div className="h-14 px-5 flex items-center gap-2 border-b border-[#E2E8F0]">
          <div className="w-7 h-7 bg-[#1A1A2E] rounded-sm flex items-center justify-center">
            <Scale className="w-4 h-4 text-white" />
          </div>
          <span className="text-base font-bold tracking-tight text-[#1A1A2E]">Associate</span>
        </div>

        {/* Nav */}
        <nav className="flex-1 py-4 px-3 space-y-0.5">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              data-testid={`nav-${item.label.toLowerCase()}`}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-sm text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-[#1A1A2E] text-white'
                    : 'text-[#4A4A4A] hover:bg-[#E2E8F0] hover:text-[#0D0D0D]'
                }`
              }
            >
              <item.icon className="w-4 h-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>

        {/* User */}
        <div className="border-t border-[#E2E8F0] p-3">
          <div
            className="flex items-center gap-2 px-3 py-2 rounded-sm hover:bg-[#E2E8F0] cursor-pointer transition-colors relative"
            onClick={() => setShowUserMenu(!showUserMenu)}
            data-testid="user-menu-trigger"
          >
            {user?.picture ? (
              <img src={user.picture} alt="" className="w-7 h-7 rounded-full" />
            ) : (
              <div className="w-7 h-7 bg-[#1A1A2E] rounded-full flex items-center justify-center">
                <User className="w-3.5 h-3.5 text-white" />
              </div>
            )}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-[#0D0D0D] truncate">{user?.name || 'User'}</p>
              <p className="text-[10px] text-[#64748B] truncate">{user?.email || ''}</p>
            </div>
            <ChevronDown className="w-3 h-3 text-[#64748B]" />
          </div>
          {showUserMenu && (
            <div className="absolute bottom-16 left-3 right-3 bg-white border border-[#E2E8F0] rounded-sm shadow-[0_4px_16px_rgba(0,0,0,0.08)] z-50">
              <button
                onClick={handleLogout}
                className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-[#991B1B] hover:bg-[#FEF2F2] transition-colors"
                data-testid="logout-btn"
              >
                <LogOut className="w-4 h-4" />
                Sign Out
              </button>
            </div>
          )}
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 min-w-0 flex flex-col overflow-hidden">
        <Outlet />
      </main>
    </div>
  );
}
