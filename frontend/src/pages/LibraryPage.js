import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import {
  BookOpen, Plus, FileText, Tag, Search, Trash2, X
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL ? `${process.env.REACT_APP_BACKEND_URL}/api` : '/api';

const ITEM_TYPES = [
  { id: 'template', label: 'Template' },
  { id: 'playbook', label: 'Playbook' },
  { id: 'memo', label: 'Internal Memo' },
  { id: 'precedent', label: 'Precedent' },
  { id: 'annotation', label: 'Annotation' },
];

export default function LibraryPage() {
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [newItem, setNewItem] = useState({ title: '', content: '', item_type: 'template', tags: '' });
  const [selectedItem, setSelectedItem] = useState(null);

  useEffect(() => { fetchItems(); }, []);

  const fetchItems = async () => {
    try {
      const res = await fetch(`${API}/library`, { credentials: 'include' });
      if (res.ok) setItems(await res.json());
    } catch {}
  };

  const handleCreate = async () => {
    if (!newItem.title.trim()) return;
    try {
      const res = await fetch(`${API}/library`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          ...newItem,
          tags: newItem.tags.split(',').map(t => t.trim()).filter(Boolean),
        }),
      });
      if (res.ok) {
        const item = await res.json();
        setItems(prev => [item, ...prev]);
        setNewItem({ title: '', content: '', item_type: 'template', tags: '' });
        setShowForm(false);
      }
    } catch {}
  };

  const handleDelete = async (itemId) => {
    try {
      await fetch(`${API}/library/${itemId}`, { method: 'DELETE', credentials: 'include' });
      setItems(prev => prev.filter(i => i.item_id !== itemId));
      if (selectedItem?.item_id === itemId) setSelectedItem(null);
    } catch {}
  };

  const filtered = items.filter(i =>
    i.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    i.content.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="flex flex-col h-full page-bg" data-testid="library-page">
      <div className="h-14 border-b border-[#E2E8F0] px-6 flex items-center justify-between shrink-0 glass-header">
        <div className="flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-[#64748B]" />
          <h1 className="text-base font-semibold text-[#0A0A0A]">Library</h1>
          <span className="text-xs text-[#64748B] font-mono ml-2">{items.length} items</span>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-[#0A0A0A] text-white text-xs font-medium rounded-[12px] hover:bg-[#0D0D0D] transition-colors btn-black-pill"
          data-testid="add-library-item-btn"
        >
          <Plus className="w-3 h-3" /> Add Item
        </button>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* List */}
        <div className="w-[360px] border-r border-[#E2E8F0] flex flex-col shrink-0">
          <div className="p-3">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-[#94A3B8] absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search library..."
                className="w-full pl-9 pr-3 py-2 text-sm glass-input"
                data-testid="library-search"
              />
            </div>
          </div>

          <div className="flex-1 overflow-y-auto px-3 pb-3 space-y-1">
            {filtered.map((item) => (
              <div
                key={item.item_id}
                onClick={() => setSelectedItem(item)}
                className={`p-3 rounded-[12px] cursor-pointer transition-colors border ${
                  selectedItem?.item_id === item.item_id
                    ? 'border-[#0A0A0A] bg-[#F8FAFC]'
                    : 'border-transparent hover:bg-[#F8FAFC]'
                }`}
                data-testid={`library-item-${item.item_id}`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-sm font-medium text-[#0D0D0D]">{item.title}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-[10px] font-mono text-[#64748B] bg-[#F1F5F9] px-1.5 py-0.5 rounded-[100px]">{item.item_type}</span>
                      {item.tags?.map((tag, i) => (
                        <span key={i} className="text-[10px] text-[#94A3B8]">#{tag}</span>
                      ))}
                    </div>
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); handleDelete(item.item_id); }}
                    className="text-[#CBD5E1] hover:text-[#333] transition-colors"
                    data-testid={`delete-library-${item.item_id}`}
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Content / Form */}
        <div className="flex-1 overflow-y-auto p-6">
          {showForm ? (
            <div className="max-w-lg">
              <h2 className="text-lg font-semibold text-[#0A0A0A] mb-4">Add to Library</h2>
              <div className="space-y-4">
                <div>
                  <label className="text-xs font-semibold text-[#4A4A4A] uppercase tracking-wider mb-1.5 block">Title</label>
                  <input
                    type="text"
                    value={newItem.title}
                    onChange={(e) => setNewItem(prev => ({ ...prev, title: e.target.value }))}
                    className="w-full px-3 py-2 text-sm glass-input"
                    data-testid="new-item-title"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-[#4A4A4A] uppercase tracking-wider mb-1.5 block">Type</label>
                  <select
                    value={newItem.item_type}
                    onChange={(e) => setNewItem(prev => ({ ...prev, item_type: e.target.value }))}
                    className="w-full px-3 py-2 text-sm glass-input"
                    data-testid="new-item-type"
                  >
                    {ITEM_TYPES.map(t => <option key={t.id} value={t.id}>{t.label}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs font-semibold text-[#4A4A4A] uppercase tracking-wider mb-1.5 block">Content</label>
                  <textarea
                    value={newItem.content}
                    onChange={(e) => setNewItem(prev => ({ ...prev, content: e.target.value }))}
                    className="w-full px-3 py-2 text-sm glass-input min-h-[200px]"
                    data-testid="new-item-content"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-[#4A4A4A] uppercase tracking-wider mb-1.5 block">Tags (comma-separated)</label>
                  <input
                    type="text"
                    value={newItem.tags}
                    onChange={(e) => setNewItem(prev => ({ ...prev, tags: e.target.value }))}
                    placeholder="gst, compliance, notice"
                    className="w-full px-3 py-2 text-sm glass-input"
                    data-testid="new-item-tags"
                  />
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={handleCreate}
                    className="bg-[#0A0A0A] text-white px-4 py-2 text-sm font-medium hover:bg-[#0D0D0D] transition-colors btn-black-pill"
                    data-testid="save-library-item"
                  >
                    Save
                  </button>
                  <button
                    onClick={() => setShowForm(false)}
                    className="border border-[#E2E8F0] px-4 py-2 text-sm text-[#4A4A4A] hover:bg-[#F8FAFC] transition-colors btn-ghost"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          ) : selectedItem ? (
            <div>
              <div className="mb-4">
                <h2 className="text-lg font-semibold text-[#0D0D0D]">{selectedItem.title}</h2>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-xs font-mono text-[#64748B] bg-[#F1F5F9] px-2 py-0.5 rounded-[12px]">{selectedItem.item_type}</span>
                  {selectedItem.tags?.map((tag, i) => (
                    <span key={i} className="text-xs text-[#94A3B8]">#{tag}</span>
                  ))}
                  <span className="text-xs text-[#94A3B8] ml-auto">
                    {new Date(selectedItem.created_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
              <div className="border border-[#E2E8F0] rounded-[12px] p-6 bg-white whitespace-pre-wrap text-[15px] leading-7 text-[#0D0D0D]">
                {selectedItem.content}
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <BookOpen className="w-8 h-8 text-[#CBD5E1] mx-auto mb-3" />
                <p className="text-sm text-[#94A3B8]">Select an item or add new knowledge</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
