import React, { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FolderOpen, Folder, ChevronRight, X, Plus, Search, Upload, Loader2, Home } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const API = process.env.NODE_ENV === 'development' ? '/api' : '/api';

/**
 * Google Drive folder picker modal.
 * Browse user's Drive folders with breadcrumb navigation, search, and folder creation.
 *
 * Props:
 *   isOpen: boolean
 *   onClose: () => void
 *   onSelect: (folderId: string, folderName: string) => void
 */
export function DriveFolderPicker({ isOpen, onClose, onSelect }) {
  const { getToken } = useAuth();
  const [folders, setFolders] = useState([]);
  const [breadcrumb, setBreadcrumb] = useState([{ id: 'root', name: 'My Drive' }]);
  const [parentId, setParentId] = useState('root');
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState('');
  const [creating, setCreating] = useState(false);
  const searchTimer = useRef(null);

  const fetchFolders = useCallback(async (pid, q = '') => {
    setLoading(true);
    try {
      let token = '';

      try { token = await getToken() || token; } catch { /**/ }
      try { token = await getToken() || token; } catch {}
      const params = new URLSearchParams();
      if (pid && pid !== 'root') params.set('parent_id', pid);
      if (q) params.set('q', q);
      const res = await fetch(`${API}/google/folders?${params}`, {
        headers: { 'Authorization': `Bearer ${token}` },
        credentials: 'include',
      });
      if (!res.ok) throw new Error('Failed');
      const data = await res.json();
      setFolders(data.folders || []);
      if (data.breadcrumb) setBreadcrumb(data.breadcrumb);
    } catch (e) {
      console.error('fetch folders failed', e);
      setFolders([]);
    } finally {
      setLoading(false);
    }
  }, [getToken]);

  useEffect(() => {
    if (isOpen) { fetchFolders(parentId); }
  }, [isOpen, parentId, fetchFolders]);

  const handleSearch = (val) => {
    setSearch(val);
    if (searchTimer.current) clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => fetchFolders(parentId, val), 300);
  };

  const navigateTo = (folder) => {
    setBreadcrumb(prev => [...prev, folder]);
    setParentId(folder.id);
    setSearch('');
  };

  const navigateBreadcrumb = (index) => {
    const newCrumb = breadcrumb.slice(0, index + 1);
    setBreadcrumb(newCrumb);
    setParentId(newCrumb[newCrumb.length - 1].id);
    setSearch('');
  };

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      let token = '';

      try { token = await getToken() || token; } catch { /**/ }
      try { token = await getToken() || token; } catch {}
      const fd = new FormData();
      fd.append('name', newName.trim());
      if (parentId && parentId !== 'root') fd.append('parent_id', parentId);
      const res = await fetch(`${API}/google/folders/create`, {
        method: 'POST', body: fd,
        headers: { 'Authorization': `Bearer ${token}` },
        credentials: 'include',
      });
      if (!res.ok) throw new Error('Create failed');
      setNewName(''); setShowCreate(false);
      await fetchFolders(parentId, search);
    } catch (e) {
      console.error('create failed', e);
    } finally { setCreating(false); }
  };

  const handleUpload = () => {
    const current = breadcrumb[breadcrumb.length - 1];
    onSelect?.(current.id, current.name);
    onClose?.();
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={onClose}
            style={{
              position: 'fixed', inset: 0, zIndex: 1000,
              background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(8px)',
            }}
          />
          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
            style={{
              position: 'fixed', top: '50%', left: '50%', transform: 'translate(-50%,-50%)',
              zIndex: 1001, width: '90vw', maxWidth: 560, maxHeight: '80vh',
              background: '#fff', borderRadius: 16,
              boxShadow: '0 30px 80px rgba(0,0,0,0.25), 0 0 0 1px rgba(0,0,0,0.05)',
              display: 'flex', flexDirection: 'column', overflow: 'hidden',
              fontFamily: "'Inter', sans-serif",
            }}
          >
            {/* Header */}
            <div style={{ padding: '16px 20px', borderBottom: '1px solid #EBEBEB', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{ width: 32, height: 32, borderRadius: 8, background: '#F5F5F5', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <FolderOpen style={{ width: 15, height: 15, color: '#0A0A0A' }} />
                </div>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: '#0A0A0A' }}>Upload to Google Drive</div>
                  <div style={{ fontSize: 11, color: '#888', marginTop: 1 }}>Choose a folder</div>
                </div>
              </div>
              <button onClick={onClose} style={{ background: 'none', border: 'none', padding: 6, cursor: 'pointer', borderRadius: 6, color: '#888' }}>
                <X style={{ width: 16, height: 16 }} />
              </button>
            </div>

            {/* Breadcrumb */}
            <div style={{ padding: '10px 20px', display: 'flex', alignItems: 'center', gap: 4, fontSize: 12.5, borderBottom: '1px solid #F5F5F5', flexShrink: 0, overflowX: 'auto' }}>
              {breadcrumb.map((c, i) => (
                <React.Fragment key={c.id}>
                  {i > 0 && <ChevronRight style={{ width: 10, height: 10, color: '#CCC', flexShrink: 0 }} />}
                  <button onClick={() => navigateBreadcrumb(i)} style={{
                    background: 'none', border: 'none', padding: '3px 6px', borderRadius: 5,
                    color: i === breadcrumb.length - 1 ? '#0A0A0A' : '#888',
                    fontWeight: i === breadcrumb.length - 1 ? 600 : 500, cursor: 'pointer',
                    display: 'flex', alignItems: 'center', gap: 4, whiteSpace: 'nowrap',
                    fontFamily: 'inherit', fontSize: 12.5,
                  }}
                    onMouseEnter={e => e.currentTarget.style.background = '#F7F7F7'}
                    onMouseLeave={e => e.currentTarget.style.background = 'none'}>
                    {i === 0 && <Home style={{ width: 10, height: 10 }} />}
                    {c.name}
                  </button>
                </React.Fragment>
              ))}
            </div>

            {/* Search */}
            <div style={{ padding: '12px 20px', flexShrink: 0 }}>
              <div style={{ position: 'relative' }}>
                <Search style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', width: 13, height: 13, color: '#BBB' }} />
                <input
                  type="text" placeholder="Search folders..." value={search}
                  onChange={e => handleSearch(e.target.value)}
                  style={{
                    width: '100%', padding: '8px 10px 8px 32px', fontSize: 13,
                    border: '1px solid #E5E5E5', borderRadius: 8, outline: 'none',
                    fontFamily: 'inherit', color: '#111', background: '#FAFAFA',
                  }}
                />
              </div>
            </div>

            {/* Folder list */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '0 10px 10px' }}>
              {loading ? (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 40, color: '#AAA' }}>
                  <Loader2 style={{ width: 16, height: 16, animation: 'spin 0.8s linear infinite' }} />
                </div>
              ) : folders.length === 0 ? (
                <div style={{ textAlign: 'center', padding: 32, color: '#BBB', fontSize: 13 }}>
                  {search ? 'No folders match your search' : 'This folder is empty'}
                </div>
              ) : (
                folders.map(f => (
                  <motion.button
                    key={f.id}
                    onClick={() => navigateTo(f)}
                    whileHover={{ backgroundColor: '#F5F5F5', x: 2 }}
                    whileTap={{ scale: 0.99 }}
                    style={{
                      width: '100%', padding: '10px 14px', display: 'flex', alignItems: 'center',
                      gap: 10, background: 'transparent', border: 'none', borderRadius: 8,
                      cursor: 'pointer', textAlign: 'left', fontFamily: 'inherit', marginBottom: 2,
                    }}>
                    <Folder style={{ width: 16, height: 16, color: '#5F6368', flexShrink: 0 }} />
                    <span style={{ flex: 1, fontSize: 13.5, color: '#222', fontWeight: 500 }}>{f.name}</span>
                    <ChevronRight style={{ width: 12, height: 12, color: '#BBB' }} />
                  </motion.button>
                ))
              )}
            </div>

            {/* Actions */}
            <div style={{ padding: '12px 20px', borderTop: '1px solid #EBEBEB', display: 'flex', gap: 8, flexShrink: 0 }}>
              <button
                onClick={() => setShowCreate(true)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px',
                  background: '#fff', border: '1px solid #E5E5E5', borderRadius: 8,
                  fontSize: 12.5, fontWeight: 600, color: '#555', cursor: 'pointer', fontFamily: 'inherit',
                }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = '#0A0A0A'; e.currentTarget.style.color = '#0A0A0A'; }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = '#E5E5E5'; e.currentTarget.style.color = '#555'; }}>
                <Plus style={{ width: 12, height: 12 }} /> New folder
              </button>
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.97 }}
                onClick={handleUpload}
                style={{
                  flex: 1, padding: '8px 14px', background: '#0A0A0A', color: '#fff',
                  border: 'none', borderRadius: 8, fontSize: 12.5, fontWeight: 700,
                  cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                  fontFamily: 'inherit',
                }}>
                <Upload style={{ width: 12, height: 12 }} />
                Upload to "{breadcrumb[breadcrumb.length - 1].name}"
              </motion.button>
            </div>

            {/* Create folder inline */}
            <AnimatePresence>
              {showCreate && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  style={{ borderTop: '1px solid #EBEBEB', overflow: 'hidden' }}>
                  <div style={{ padding: '12px 20px', display: 'flex', gap: 8 }}>
                    <input
                      type="text" autoFocus
                      placeholder="Folder name"
                      value={newName}
                      onChange={e => setNewName(e.target.value)}
                      onKeyDown={e => { if (e.key === 'Enter') handleCreate(); else if (e.key === 'Escape') setShowCreate(false); }}
                      style={{
                        flex: 1, padding: '7px 10px', fontSize: 12.5,
                        border: '1px solid #CCC', borderRadius: 6, outline: 'none',
                        fontFamily: 'inherit',
                      }}
                    />
                    <button onClick={() => setShowCreate(false)} style={{ padding: '7px 12px', background: 'none', border: '1px solid #E5E5E5', borderRadius: 6, cursor: 'pointer', fontSize: 12, color: '#888', fontFamily: 'inherit' }}>Cancel</button>
                    <button onClick={handleCreate} disabled={creating || !newName.trim()} style={{ padding: '7px 14px', background: '#0A0A0A', color: '#fff', border: 'none', borderRadius: 6, cursor: creating ? 'default' : 'pointer', fontSize: 12, fontWeight: 600, fontFamily: 'inherit', opacity: !newName.trim() || creating ? 0.5 : 1 }}>
                      {creating ? <Loader2 style={{ width: 12, height: 12, animation: 'spin 0.8s linear infinite' }} /> : 'Create'}
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
