import React from 'react';
import { BookOpen, FileText, Database, Layers, CheckCircle2, FileUp } from 'lucide-react';
import type { DocumentItem, ProjectStats } from '../types';

interface SidebarRightProps {
  projectId: string;
  stats: ProjectStats | null;
  documents: DocumentItem[];
  loadingDocuments: boolean;
  onOpenAddDocument: () => void;
  onOpenInstructions: () => void;
}

export const SidebarRight: React.FC<SidebarRightProps> = ({
  projectId,
  stats,
  documents,
  loadingDocuments,
  onOpenAddDocument,
  onOpenInstructions,
}) => {
  return (
    <aside className="w-72 h-full bg-[#f4f1ea] border-l border-[#0d0d0d] flex flex-col justify-between shrink-0 select-none">
      {/* Top Section: Wireframe Buttons "add documents" and "project instructions" */}
      <div className="p-4 border-b border-[#0d0d0d] space-y-3 bg-[#f7f5ef]">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-bold uppercase tracking-wider text-neutral-500 font-display">
            Project Settings
          </span>
          <span className="text-[11px] font-mono text-[#0d0d0d] font-bold truncate max-w-[120px] px-2 py-0.5 rounded-[6px] bg-[#ffffff] border border-[#0d0d0d]">
            {projectId}
          </span>
        </div>

        <div className="space-y-2">
          {/* Wireframe Button: "add documents" in golden yellow */}
          <button
            onClick={onOpenAddDocument}
            className="w-full py-2.5 px-3 rounded-[14px] bg-[#ffd184] border border-[#0d0d0d] text-[#111111] font-display font-bold text-xs transition pika-btn flex items-center justify-center gap-1.5"
          >
            <FileUp className="w-3.5 h-3.5 stroke-[2.5]" />
            <span>add documents</span>
          </button>

          {/* Wireframe Button: "project instructions" in soft lavender */}
          <button
            onClick={onOpenInstructions}
            className="w-full py-2 px-3 rounded-[14px] bg-[#cfc3ff] hover:bg-[#c2b4fd] border border-[#0d0d0d] text-[#0d0d0d] font-display font-semibold text-xs transition pika-btn flex items-center justify-center gap-1.5"
          >
            <BookOpen className="w-3.5 h-3.5 stroke-[2.5]" />
            <span>project instructions</span>
          </button>
        </div>
      </div>

      {/* Middle Section: Wireframe "-project specific details" & "-resources, -extra documents" */}
      <div className="flex-1 overflow-y-auto p-4 space-y-5">
        
        {/* Wireframe: "-project specific details" */}
        <div className="space-y-2">
          <span className="text-[11px] font-bold uppercase tracking-wider text-neutral-500 font-display">
            Project Details
          </span>
          <div className="grid grid-cols-2 gap-2">
            <div className="p-3 rounded-[14px] bg-[#ffffff] border border-[#0d0d0d] pika-shadow">
              <div className="flex items-center gap-1 text-neutral-500 text-[11px] mb-1 font-mono">
                <Database className="w-3 h-3 text-[#0d0d0d]" />
                <span>Chunks</span>
              </div>
              <div className="text-xl font-extrabold text-[#0d0d0d] font-mono">
                {stats ? stats.total_chunks : 0}
              </div>
            </div>

            <div className="p-3 rounded-[14px] bg-[#ffffff] border border-[#0d0d0d] pika-shadow">
              <div className="flex items-center gap-1 text-neutral-500 text-[11px] mb-1 font-mono">
                <Layers className="w-3 h-3 text-[#0d0d0d]" />
                <span>Docs</span>
              </div>
              <div className="text-xl font-extrabold text-[#0d0d0d] font-mono">
                {documents.length}
              </div>
            </div>
          </div>
        </div>

        {/* Wireframe: "-resources" & "-extra documents" */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-neutral-500 font-display">
              Resources & Documents
            </span>
            <span className="text-[11px] font-mono text-neutral-600 font-bold">
              {documents.length}
            </span>
          </div>

          {loadingDocuments ? (
            <div className="text-xs text-neutral-500 py-3 text-center font-mono">
              Loading resources...
            </div>
          ) : documents.length === 0 ? (
            <div className="p-4 rounded-[16px] border border-dashed border-[#0d0d0d] text-center space-y-1 bg-[#ffffff]">
              <FileText className="w-5 h-5 mx-auto text-neutral-400" />
              <p className="text-xs text-[#0d0d0d] font-semibold font-display">No resources</p>
              <p className="text-[11px] text-neutral-500">
                Click "add documents" to upload files or text.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {documents.map((doc, idx) => (
                <div
                  key={doc.doc_id || idx}
                  className="p-2.5 rounded-[12px] bg-[#ffffff] border border-[#0d0d0d] pika-shadow text-xs transition"
                >
                  <div className="flex items-center justify-between gap-1.5">
                    <div className="flex items-center gap-2 truncate flex-1 min-w-0">
                      <FileText className="w-3.5 h-3.5 text-[#0d0d0d] shrink-0" />
                      <span className="truncate font-semibold text-[#0d0d0d] text-[11px] font-sans">
                        {doc.filename}
                      </span>
                    </div>
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0 stroke-[2.5]" />
                  </div>

                  <div className="mt-1.5 flex items-center justify-between text-[10px] text-neutral-500 font-mono">
                    <span>
                      {doc.chunk_count !== undefined
                        ? `${doc.chunk_count} chunks`
                        : (doc.file_size ? `${Math.round(doc.file_size / 1024)} KB` : 'indexed')}
                    </span>
                    <span className="uppercase px-1 py-0.2 rounded bg-neutral-100 border border-neutral-300">
                      {doc.file_type?.split('/')[1] || 'DOC'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Footer System Status */}
      <div className="p-3 border-t border-[#0d0d0d] bg-[#f7f5ef] text-center">
        <span className="text-[10px] text-neutral-600 font-mono font-medium">
          ChromaDB Vector + Lexical RAG
        </span>
      </div>
    </aside>
  );
};
