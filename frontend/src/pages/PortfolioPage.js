import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import {
  Briefcase, AlertTriangle, Clock, CheckCircle, Plus,
  ChevronRight, Search, Filter, RefreshCw
} from 'lucide-react';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

const RISK_COLORS = {
  HIGH: { bg: 'bg-[#FEF2F2]', text: 'text-[#991B1B]', border: 'border-[#FECACA]', dot: 'bg-[#DC2626]' },
  MEDIUM: { bg: 'bg-[#FFFBEB]', text: 'text-[#92400E]', border: 'border-[#FDE68A]', dot: 'bg-[#F59E0B]' },
  LOW: { bg: 'bg-[#F0FDF4]', text: 'text-[#166534]', border: 'border-[#BBF7D0]', dot: 'bg-[#22C55E]' },
  OVERDUE: { bg: 'bg-[#FEF2F2]', text: 'text-[#991B1B]', border: 'border-[#FECACA]', dot: 'bg-[#DC2626]' },
};

function getDeadlineStatus(deadlineStr) {
  if (!deadlineStr) return { label: 'No deadline', color: RISK_COLORS.LOW };
  const d = new Date(deadlineStr);
  const now = new Date();
  const diff = Math.ceil((d - now) / (1000 * 60 * 60 * 24));
  if (diff < 0) return { label: `${Math.abs(diff)}d overdue`, color: RISK_COLORS.OVERDUE };
  if (diff <= 3) return { label: `${diff}d left`, color: RISK_COLORS.HIGH };
  if (diff <= 7) return { label: `${diff}d left`, color: RISK_COLORS.MEDIUM };
  return { label: `${diff}d left`, color: RISK_COLORS.LOW };
}

export default function PortfolioPage() {
  const { token } = useAuth();
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filterRisk, setFilterRisk] = useState('ALL');
  const [showAddClient, setShowAddClient] = useState(false);
  const [newClient, setNewClient] = useState({ name: '', pan: '', gstin: '', entity_type: 'Company', practice_areas: [] });

  const fetchClients = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/portfolio/clients`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setClients(data.clients || []);
      }
    } catch (err) {
      console.error('Failed to fetch clients:', err);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { fetchClients(); }, [fetchClients]);

  const addClient = async () => {
    try {
      const res = await fetch(`${API_BASE}/portfolio/clients`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify(newClient)
      });
      if (res.ok) {
        setShowAddClient(false);
        setNewClient({ name: '', pan: '', gstin: '', entity_type: 'Company', practice_areas: [] });
        fetchClients();
      }
    } catch (err) {
      console.error('Failed to add client:', err);
    }
  };

  const filteredClients = clients.filter(c => {
    const matchSearch = !search || c.name?.toLowerCase().includes(search.toLowerCase()) || c.pan?.includes(search.toUpperCase());
    const matchRisk = filterRisk === 'ALL' || c.risk_level === filterRisk;
    return matchSearch && matchRisk;
  });

  // Stats
  const highRisk = clients.filter(c => c.risk_level === 'HIGH').length;
  const overdue = clients.filter(c => {
    if (!c.next_deadline) return false;
    return new Date(c.next_deadline) < new Date();
  }).length;
  const activeMatters = clients.reduce((acc, c) => acc + (c.active_matters || 0), 0);

  return (
    <div className="flex-1 flex flex-col overflow-hidden" data-testid="portfolio-page">
      {/* Header */}
      <div className="h-14 px-6 flex items-center justify-between border-b border-[#E2E8F0] shrink-0">
        <div className="flex items-center gap-3">
          <Briefcase className="w-4 h-4 text-[#1A1A2E]" />
          <h1 className="text-sm font-bold tracking-wider uppercase text-[#1A1A2E]">Portfolio Command Center</h1>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => fetchClients()}
            className="text-xs text-[#64748B] hover:text-[#0D0D0D] p-2 rounded-sm hover:bg-[#F1F5F9] transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setShowAddClient(true)}
            className="flex items-center gap-1.5 text-xs font-medium bg-[#1A1A2E] text-white px-3 py-1.5 rounded-sm hover:bg-[#0D0D0D] transition-colors"
            data-testid="add-client-btn"
          >
            <Plus className="w-3.5 h-3.5" /> Add Client
          </button>
        </div>
      </div>

      {/* Stats Bar */}
      <div className="px-6 py-4 border-b border-[#E2E8F0] flex items-center gap-6 shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-[#1A1A2E]" />
          <span className="text-xs text-[#64748B]">Total Clients</span>
          <span className="text-sm font-bold text-[#0D0D0D]">{clients.length}</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-[#DC2626]" />
          <span className="text-xs text-[#64748B]">High Risk</span>
          <span className="text-sm font-bold text-[#991B1B]">{highRisk}</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-[#F59E0B]" />
          <span className="text-xs text-[#64748B]">Overdue</span>
          <span className="text-sm font-bold text-[#92400E]">{overdue}</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-[#22C55E]" />
          <span className="text-xs text-[#64748B]">Active Matters</span>
          <span className="text-sm font-bold text-[#166534]">{activeMatters}</span>
        </div>
      </div>

      {/* Search & Filter */}
      <div className="px-6 py-3 border-b border-[#E2E8F0] flex items-center gap-3 shrink-0">
        <div className="flex items-center gap-2 flex-1 bg-[#F8FAFC] border border-[#E2E8F0] rounded-sm px-3 py-2">
          <Search className="w-3.5 h-3.5 text-[#94A3B8]" />
          <input
            type="text"
            placeholder="Search by client name or PAN..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="flex-1 bg-transparent text-sm text-[#0D0D0D] outline-none placeholder:text-[#94A3B8]"
            data-testid="portfolio-search"
          />
        </div>
        <div className="flex items-center gap-1">
          {['ALL', 'HIGH', 'MEDIUM', 'LOW'].map(level => (
            <button
              key={level}
              onClick={() => setFilterRisk(level)}
              className={`text-[10px] font-mono px-2 py-1 rounded-sm border transition-colors ${
                filterRisk === level ? 'bg-[#1A1A2E] text-white border-[#1A1A2E]' : 'bg-white text-[#64748B] border-[#E2E8F0] hover:bg-[#F8FAFC]'
              }`}
            >
              {level}
            </button>
          ))}
        </div>
      </div>

      {/* Client List */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-2">
        {loading ? (
          <div className="text-center py-8 text-sm text-[#94A3B8]">Loading clients...</div>
        ) : filteredClients.length === 0 ? (
          <div className="text-center py-16">
            <Briefcase className="w-8 h-8 text-[#CBD5E1] mx-auto mb-3" />
            <p className="text-sm text-[#64748B]">{clients.length === 0 ? 'No clients yet. Add your first client.' : 'No clients match your search.'}</p>
          </div>
        ) : (
          filteredClients.map((client, i) => {
            const deadline = getDeadlineStatus(client.next_deadline);
            const riskStyle = RISK_COLORS[client.risk_level] || RISK_COLORS.LOW;
            return (
              <div
                key={client.client_id || i}
                className={`border ${riskStyle.border} rounded-sm p-4 hover:shadow-sm transition-shadow cursor-pointer ${riskStyle.bg}`}
                data-testid={`client-card-${i}`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-2.5 h-2.5 rounded-full ${riskStyle.dot}`} />
                    <div>
                      <h3 className="text-sm font-semibold text-[#0D0D0D]">{client.name}</h3>
                      <div className="flex items-center gap-3 mt-0.5">
                        <span className="text-[10px] font-mono text-[#64748B]">PAN: {client.pan || 'N/A'}</span>
                        {client.gstin && <span className="text-[10px] font-mono text-[#64748B]">GSTIN: {client.gstin}</span>}
                        <span className="text-[10px] text-[#94A3B8]">{client.entity_type}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <div className={`text-[10px] font-mono font-bold ${riskStyle.text}`}>{client.risk_level || 'LOW'} RISK</div>
                      <div className={`text-[10px] ${deadline.color.text}`}>
                        <Clock className="w-3 h-3 inline mr-0.5" />{deadline.label}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-[10px] text-[#64748B]">{client.active_matters || 0} matters</div>
                      <div className="text-[10px] text-[#94A3B8]">{client.practice_areas?.join(', ') || 'General'}</div>
                    </div>
                    <ChevronRight className="w-4 h-4 text-[#CBD5E1]" />
                  </div>
                </div>
                {/* Conflict Warning */}
                {client.conflicts && client.conflicts.length > 0 && (
                  <div className="mt-2 px-3 py-1.5 bg-[#FEF2F2] border border-[#FECACA] rounded-sm flex items-center gap-2">
                    <AlertTriangle className="w-3.5 h-3.5 text-[#DC2626]" />
                    <span className="text-[11px] text-[#991B1B] font-medium">
                      CONFLICT: {client.conflicts.join('; ')}
                    </span>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Add Client Modal */}
      {showAddClient && (
        <div className="fixed inset-0 bg-black/20 flex items-center justify-center z-50" onClick={() => setShowAddClient(false)}>
          <div className="bg-white border border-[#E2E8F0] rounded-sm shadow-lg w-[480px] p-6" onClick={e => e.stopPropagation()}>
            <h2 className="text-sm font-bold tracking-wider uppercase text-[#1A1A2E] mb-4">Add Client</h2>
            <div className="space-y-3">
              <input
                type="text" placeholder="Client / Company Name *"
                value={newClient.name} onChange={e => setNewClient({...newClient, name: e.target.value})}
                className="w-full px-3 py-2 text-sm border border-[#E2E8F0] rounded-sm outline-none focus:border-[#1A1A2E]"
                data-testid="add-client-name"
              />
              <div className="flex gap-3">
                <input
                  type="text" placeholder="PAN"
                  value={newClient.pan} onChange={e => setNewClient({...newClient, pan: e.target.value.toUpperCase()})}
                  className="flex-1 px-3 py-2 text-sm border border-[#E2E8F0] rounded-sm outline-none focus:border-[#1A1A2E] font-mono"
                />
                <input
                  type="text" placeholder="GSTIN (optional)"
                  value={newClient.gstin} onChange={e => setNewClient({...newClient, gstin: e.target.value.toUpperCase()})}
                  className="flex-1 px-3 py-2 text-sm border border-[#E2E8F0] rounded-sm outline-none focus:border-[#1A1A2E] font-mono"
                />
              </div>
              <select
                value={newClient.entity_type} onChange={e => setNewClient({...newClient, entity_type: e.target.value})}
                className="w-full px-3 py-2 text-sm border border-[#E2E8F0] rounded-sm outline-none focus:border-[#1A1A2E]"
              >
                <option>Company</option>
                <option>LLP</option>
                <option>Partnership</option>
                <option>Individual</option>
                <option>Trust</option>
                <option>HUF</option>
              </select>
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button
                onClick={() => setShowAddClient(false)}
                className="text-xs text-[#64748B] px-3 py-1.5 border border-[#E2E8F0] rounded-sm hover:bg-[#F8FAFC]"
              >Cancel</button>
              <button
                onClick={addClient}
                disabled={!newClient.name}
                className="text-xs font-medium bg-[#1A1A2E] text-white px-4 py-1.5 rounded-sm hover:bg-[#0D0D0D] disabled:opacity-50"
                data-testid="save-client-btn"
              >Save Client</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
