import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, Check, ExternalLink, Upload } from 'lucide-react';
import { DriveFolderPicker } from './DriveFolderPicker';
import { useGoogleDriveConnection } from './GoogleDriveConnect';
import { useAuth } from '../context/AuthContext';

const API = process.env.NODE_ENV === 'development' ? '/api' : '/api';

// Google Drive logo
const DriveIcon = ({ size = 14 }) => (
  <svg width={size} height={size} viewBox="0 0 87.3 78">
    <path fill="#0066da" d="M6.6 66.85l3.85 6.65c.8 1.4 1.95 2.5 3.3 3.3l13.75-23.8h-27.5c0 1.55.4 3.1 1.2 4.5z"/>
    <path fill="#00ac47" d="M43.65 25l-13.75-23.8c-1.35.8-2.5 1.9-3.3 3.3l-25.4 44a9.06 9.06 0 0 0-1.2 4.5h27.5z"/>
    <path fill="#ea4335" d="M73.55 76.8c1.35-.8 2.5-1.9 3.3-3.3l1.6-2.75 7.65-13.25c.8-1.4 1.2-2.95 1.2-4.5h-27.502l5.852 11.5z"/>
    <path fill="#00832d" d="M43.65 25l13.75-23.8c-1.35-.8-2.9-1.2-4.5-1.2h-18.5c-1.6 0-3.15.45-4.5 1.2z"/>
    <path fill="#2684fc" d="M59.8 53h-32.3l-13.75 23.8c1.35.8 2.9 1.2 4.5 1.2h50.8c1.6 0 3.15-.45 4.5-1.2z"/>
    <path fill="#ffba00" d="M73.4 26.5l-12.7-22c-.8-1.4-1.95-2.5-3.3-3.3l-13.75 23.8 16.15 28h27.45c0-1.55-.4-3.1-1.2-4.5z"/>
  </svg>
);

/**
 * Drive upload button — next to download button on generated files
 *
 * Props:
 *   fileId: the backend agent file_id (used to upload the backend-stored file to Drive)
 *   fileName: display name
 */
export function DriveUploadButton({ fileId, fileName }) {
  const { status, connect } = useGoogleDriveConnection();
  const { getToken } = useAuth();
  const [picking, setPicking] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);  // { drive_url, drive_name, converted }
  const [error, setError] = useState(null);

  const handleUpload = async (folderId, folderName) => {
    setUploading(true);
    setError(null);
    try {
      let token = '';

      try { token = await getToken() || token; } catch { /**/ }
      try { token = await getToken() || token; } catch {}
      const fd = new FormData();
      fd.append('file_id', fileId);
      if (folderId && folderId !== 'root') fd.append('folder_id', folderId);
      fd.append('convert', 'true');
      const res = await fetch(`${API}/google/upload`, {
        method: 'POST', body: fd,
        headers: { 'Authorization': `Bearer ${token}` },
        credentials: 'include',
      });
      if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
      const data = await res.json();
      setResult({ ...data, folder_name: folderName });
      setTimeout(() => setResult(null), 6000);  // clear toast after 6s
    } catch (e) {
      console.error(e);
      setError(e.message || 'Upload failed');
      setTimeout(() => setError(null), 5000);
    } finally {
      setUploading(false);
    }
  };

  // Not connected → show connect-prompting button
  if (!status.connected) {
    return (
      <motion.button
        whileHover={{ scale: 1.03, borderColor: '#0A0A0A' }}
        whileTap={{ scale: 0.97 }}
        onClick={connect}
        title="Connect Google Drive first"
        style={{
          display: 'inline-flex', alignItems: 'center', gap: 5,
          padding: '5px 10px', background: '#fff',
          border: '1px solid #E5E5E5', borderRadius: 7,
          fontSize: 11.5, fontWeight: 600, color: '#666',
          cursor: 'pointer', fontFamily: "'Inter', sans-serif",
          transition: 'all 0.2s',
        }}>
        <DriveIcon size={12} />
        Connect Drive
      </motion.button>
    );
  }

  return (
    <>
      <motion.button
        whileHover={{ scale: 1.03, borderColor: '#0A0A0A' }}
        whileTap={{ scale: 0.97 }}
        onClick={() => setPicking(true)}
        disabled={uploading}
        title="Upload to Google Drive"
        style={{
          display: 'inline-flex', alignItems: 'center', gap: 5,
          padding: '5px 10px', background: '#fff',
          border: '1px solid #E5E5E5', borderRadius: 7,
          fontSize: 11.5, fontWeight: 600, color: '#444',
          cursor: uploading ? 'default' : 'pointer', fontFamily: "'Inter', sans-serif",
          opacity: uploading ? 0.6 : 1,
          transition: 'all 0.2s',
        }}>
        {uploading ? (
          <Loader2 style={{ width: 12, height: 12, animation: 'spin 0.8s linear infinite' }} />
        ) : (
          <DriveIcon size={12} />
        )}
        {uploading ? 'Uploading…' : 'Save to Drive'}
      </motion.button>

      <DriveFolderPicker
        isOpen={picking}
        onClose={() => setPicking(false)}
        onSelect={handleUpload}
      />

      {/* Success toast */}
      <AnimatePresence>
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 30, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.9 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
            style={{
              position: 'fixed', bottom: 28, right: 28, zIndex: 2000,
              background: '#fff', border: '1px solid #E5E5E5',
              borderRadius: 12, padding: '14px 18px',
              display: 'flex', alignItems: 'center', gap: 12,
              boxShadow: '0 20px 60px rgba(0,0,0,0.15)',
              fontFamily: "'Inter', sans-serif",
              maxWidth: 360,
            }}>
            <div style={{ width: 32, height: 32, borderRadius: 8, background: 'rgba(34,197,94,0.1)', border: '1px solid rgba(34,197,94,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
              <Check style={{ width: 14, height: 14, color: '#22C55E', strokeWidth: 2.5 }} />
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#0A0A0A', marginBottom: 2 }}>Uploaded to Drive</div>
              <div style={{ fontSize: 11, color: '#888', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {result.drive_name || fileName} → {result.folder_name || 'My Drive'}
              </div>
            </div>
            {result.drive_url && (
              <a href={result.drive_url} target="_blank" rel="noopener noreferrer"
                style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 11, fontWeight: 600, color: '#0A0A0A', padding: '5px 10px', border: '1px solid #E5E5E5', borderRadius: 6, textDecoration: 'none', flexShrink: 0 }}>
                Open <ExternalLink style={{ width: 10, height: 10 }} />
              </a>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Error toast */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 20 }}
            style={{
              position: 'fixed', bottom: 28, right: 28, zIndex: 2000,
              background: '#fff', border: '1px solid rgba(239,68,68,0.3)',
              borderRadius: 12, padding: '14px 18px',
              fontSize: 12, color: '#EF4444', fontWeight: 600,
              boxShadow: '0 20px 60px rgba(0,0,0,0.15)',
              fontFamily: "'Inter', sans-serif",
            }}>
            {error}
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
