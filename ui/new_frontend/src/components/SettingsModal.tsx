import React, { useEffect, useState } from 'react';
import { CheckCircle2, RefreshCw, Server, X, AlertCircle } from 'lucide-react';
import { api, getApiBase, setApiBase } from '../services/api';
import type { HealthStatus } from '../types';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onRefreshProjects: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose, onRefreshProjects }) => {
  const [apiUrl, setApiUrl] = useState(getApiBase());
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [pingMs, setPingMs] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const checkConnection = async (targetUrl?: string) => {
    setLoading(true);
    setError(null);
    const start = performance.now();
    try {
      if (targetUrl) {
        setApiBase(targetUrl);
      }
      const data = await api.getHealth();
      const end = performance.now();
      setHealth(data);
      setPingMs(Math.round(end - start));
      onRefreshProjects();
    } catch (err: any) {
      setHealth(null);
      setPingMs(null);
      setError(err.message || 'Failed to connect to backend.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      setApiUrl(getApiBase());
      checkConnection();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#0d0d0d]/50 backdrop-blur-xs p-4">
      <div className="w-full max-w-md rounded-[24px] bg-[#ffffff] border border-[#0d0d0d] p-6 pika-shadow-lg text-[#0d0d0d]">
        <div className="flex items-center justify-between pb-4 border-b border-[#0d0d0d]">
          <div className="flex items-center gap-2 font-display font-bold text-base text-[#0d0d0d]">
            <Server className="w-4 h-4 text-[#0d0d0d]" />
            <span>Backend Telemetry</span>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-[8px] text-neutral-500 hover:text-black hover:bg-neutral-100 transition"
          >
            <X className="w-4 h-4 stroke-[2.5]" />
          </button>
        </div>

        <div className="mt-4 space-y-4">
          <div>
            <label className="block text-[11px] font-display font-bold uppercase tracking-wider text-neutral-600 mb-1.5">
              Slate API Base URL
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={apiUrl}
                onChange={(e) => setApiUrl(e.target.value)}
                placeholder="http://127.0.0.1:8000"
                className="flex-1 px-3 py-2 text-xs rounded-[12px] bg-[#fcfaf7] border border-[#0d0d0d] text-[#0d0d0d] focus:outline-none focus:ring-1 focus:ring-[#0d0d0d] font-mono"
              />
              <button
                onClick={() => checkConnection(apiUrl)}
                disabled={loading}
                className="px-4 py-2 bg-[#ffd184] border border-[#0d0d0d] hover:bg-[#ffc666] disabled:opacity-50 text-[#111111] rounded-[12px] text-xs font-display font-bold transition pika-btn flex items-center gap-1.5"
              >
                {loading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : 'Test'}
              </button>
            </div>
          </div>

          <div className="p-4 rounded-[16px] bg-[#fcfaf7] border border-[#0d0d0d] space-y-2">
            <div className="text-[10px] font-display font-bold uppercase tracking-wider text-neutral-500">
              System Health
            </div>
            {health ? (
              <div className="space-y-1.5 text-xs font-mono">
                <div className="flex items-center gap-2 text-emerald-800 font-bold">
                  <CheckCircle2 className="w-4 h-4 stroke-[2.5]" />
                  <span>Online ({health.status})</span>
                  {pingMs !== null && (
                    <span className="text-[11px] text-neutral-500 font-normal">· {pingMs}ms latency</span>
                  )}
                </div>
                <div className="text-[11px] text-neutral-600">
                  <span className="text-neutral-400">Version:</span> {health.version}
                </div>
                <div className="text-[11px] text-neutral-600 truncate">
                  <span className="text-neutral-400">Chroma Dir:</span> {health.chroma_dir}
                </div>
              </div>
            ) : error ? (
              <div className="flex items-start gap-2 text-rose-700 text-xs font-mono">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            ) : (
              <div className="text-xs text-neutral-500 font-mono">Connecting...</div>
            )}
          </div>
        </div>

        <div className="mt-5 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-[#0d0d0d] hover:bg-neutral-800 text-white text-xs font-display font-bold rounded-[12px] transition pika-btn"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
