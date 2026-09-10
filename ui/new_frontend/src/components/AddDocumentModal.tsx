import React, { useState } from 'react';
import { UploadCloud, FileText, X, Check, Loader2, AlertCircle } from 'lucide-react';
import { api } from '../services/api';

interface AddDocumentModalProps {
  isOpen: boolean;
  projectId: string;
  onClose: () => void;
  onDocumentAdded: () => void;
}

export const AddDocumentModal: React.FC<AddDocumentModalProps> = ({
  isOpen,
  projectId,
  onClose,
  onDocumentAdded,
}) => {
  const [tab, setTab] = useState<'upload' | 'text'>('upload');
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);

  const [textTitle, setTextTitle] = useState('');
  const [textContent, setTextContent] = useState('');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleUploadFile = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    setSuccessMsg(null);
    try {
      await api.uploadDocument(projectId, file);
      setSuccessMsg(`"${file.name}" ingested successfully!`);
      setFile(null);
      onDocumentAdded();
      setTimeout(() => {
        setSuccessMsg(null);
        onClose();
      }, 1000);
    } catch (err: any) {
      setError(err.message || 'File upload failed');
    } finally {
      setLoading(false);
    }
  };

  const handleIngestText = async () => {
    if (!textContent.trim()) return;
    setLoading(true);
    setError(null);
    setSuccessMsg(null);
    try {
      await api.ingestText(projectId, textContent, textTitle || 'Note');
      setSuccessMsg('Text content ingested successfully!');
      setTextContent('');
      setTextTitle('');
      onDocumentAdded();
      setTimeout(() => {
        setSuccessMsg(null);
        onClose();
      }, 1000);
    } catch (err: any) {
      setError(err.message || 'Text ingestion failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#0d0d0d]/50 backdrop-blur-xs p-4">
      <div className="w-full max-w-lg rounded-[24px] bg-[#ffffff] border border-[#0d0d0d] p-6 sm:p-7 pika-shadow-lg text-[#0d0d0d]">
        <div className="flex items-center justify-between pb-4 border-b border-[#0d0d0d]">
          <div className="flex items-center gap-2 font-display font-bold text-base text-[#0d0d0d]">
            <UploadCloud className="w-5 h-5 text-[#0d0d0d]" />
            <span>Add Documents —</span>
            <span className="font-mono text-xs px-2 py-0.5 rounded-[6px] bg-[#ffd184] border border-[#0d0d0d]">{projectId}</span>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-[8px] text-neutral-500 hover:text-black hover:bg-neutral-100 transition"
          >
            <X className="w-4 h-4 stroke-[2.5]" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-[#0d0d0d] mt-4">
          <button
            onClick={() => { setTab('upload'); setError(null); }}
            className={`flex-1 py-2.5 text-xs font-display font-bold border-b-2 flex items-center justify-center gap-1.5 transition ${
              tab === 'upload'
                ? 'border-[#0d0d0d] text-[#0d0d0d] bg-[#ffd184]/20'
                : 'border-transparent text-neutral-500 hover:text-black'
            }`}
          >
            <UploadCloud className="w-3.5 h-3.5" />
            File Ingestion
          </button>
          <button
            onClick={() => { setTab('text'); setError(null); }}
            className={`flex-1 py-2.5 text-xs font-display font-bold border-b-2 flex items-center justify-center gap-1.5 transition ${
              tab === 'text'
                ? 'border-[#0d0d0d] text-[#0d0d0d] bg-[#ffd184]/20'
                : 'border-transparent text-neutral-500 hover:text-black'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            Raw Text
          </button>
        </div>

        {error && (
          <div className="mt-3 p-3 rounded-[12px] bg-rose-50 border border-rose-300 text-rose-800 text-xs flex items-center gap-2 font-mono">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {successMsg && (
          <div className="mt-3 p-3 rounded-[12px] bg-emerald-50 border border-emerald-300 text-emerald-800 text-xs flex items-center gap-2 font-mono font-semibold">
            <Check className="w-4 h-4 shrink-0 stroke-[3]" />
            <span>{successMsg}</span>
          </div>
        )}

        <div className="mt-5">
          {tab === 'upload' ? (
            <div className="space-y-4">
              <div
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-[18px] p-6 text-center transition cursor-pointer ${
                  dragActive
                    ? 'border-[#0d0d0d] bg-[#ffd184]/20'
                    : 'border-[#0d0d0d] hover:bg-[#fcfaf7] bg-[#f7f5ef]'
                }`}
                onClick={() => document.getElementById('file-input')?.click()}
              >
                <input
                  id="file-input"
                  type="file"
                  onChange={(e) => e.target.files?.[0] && setFile(e.target.files[0])}
                  className="hidden"
                  accept=".pdf,.txt,.md,.markdown,.docx,.csv,.json"
                />
                <UploadCloud className="w-8 h-8 mx-auto text-[#0d0d0d] mb-2" />
                <p className="text-xs font-bold text-[#0d0d0d] font-display">
                  {file ? file.name : 'Click to choose file or drag and drop'}
                </p>
                <p className="text-[11px] text-neutral-500 mt-1 font-mono">
                  PDF, Markdown, TXT, DOCX (up to 50MB)
                </p>
              </div>

              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 text-xs font-semibold text-neutral-600 hover:text-black transition"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleUploadFile}
                  disabled={!file || loading}
                  className="px-5 py-2.5 bg-[#ffd184] border border-[#0d0d0d] hover:bg-[#ffc666] disabled:opacity-40 text-[#111111] rounded-[14px] text-xs font-display font-bold transition pika-btn flex items-center gap-1.5"
                >
                  {loading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  Ingest File
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <div>
                <label className="block text-[11px] font-display font-bold uppercase tracking-wider text-neutral-600 mb-1">
                  Source Title
                </label>
                <input
                  type="text"
                  value={textTitle}
                  onChange={(e) => setTextTitle(e.target.value)}
                  placeholder="e.g. Research Notes or Specification"
                  className="w-full px-3.5 py-2 text-xs rounded-[12px] bg-[#fcfaf7] border border-[#0d0d0d] text-[#0d0d0d] focus:outline-none focus:ring-1 focus:ring-[#0d0d0d]"
                />
              </div>
              <div>
                <label className="block text-[11px] font-display font-bold uppercase tracking-wider text-neutral-600 mb-1">
                  Content
                </label>
                <textarea
                  rows={6}
                  value={textContent}
                  onChange={(e) => setTextContent(e.target.value)}
                  placeholder="Paste content here to chunk and index into ChromaDB..."
                  className="w-full px-3.5 py-2.5 text-xs rounded-[14px] bg-[#fcfaf7] border border-[#0d0d0d] text-[#0d0d0d] focus:outline-none focus:ring-1 focus:ring-[#0d0d0d] resize-none font-mono leading-relaxed"
                />
              </div>
              <div className="flex justify-end gap-2 pt-1">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 text-xs font-semibold text-neutral-600 hover:text-black transition"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleIngestText}
                  disabled={!textContent.trim() || loading}
                  className="px-5 py-2.5 bg-[#ffd184] border border-[#0d0d0d] hover:bg-[#ffc666] disabled:opacity-40 text-[#111111] rounded-[14px] text-xs font-display font-bold transition pika-btn flex items-center gap-1.5"
                >
                  {loading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  Ingest Text
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
