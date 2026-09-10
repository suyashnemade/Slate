import React, { useState } from 'react';
import { Plus, Settings, ChevronDown, ChevronRight, Trash2, Folder, Loader2 } from 'lucide-react';
import type { Chat } from '../types';

interface SidebarLeftProps {
  projects: string[];
  activeProjectId: string | null;
  activeChatId: string | null;
  projectChats: Record<string, Chat[]>;
  loadingProjects: boolean;
  onSelectProject: (projectId: string) => void;
  onSelectChat: (projectId: string, chatId: string) => void;
  onCreateProject: (name: string) => Promise<void>;
  onDeleteProject: (projectId: string) => Promise<void>;
  onCreateChat: (projectId: string) => Promise<void>;
  onOpenSettings: () => void;
}

export const SidebarLeft: React.FC<SidebarLeftProps> = ({
  projects,
  activeProjectId,
  activeChatId,
  projectChats,
  loadingProjects,
  onSelectProject,
  onSelectChat,
  onCreateProject,
  onDeleteProject,
  onCreateChat,
  onOpenSettings,
}) => {
  const [showNewInput, setShowNewInput] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [creating, setCreating] = useState(false);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const toggleExpand = (pId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setExpanded((prev) => ({
      ...prev,
      [pId]: !prev[pId],
    }));
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProjectName.trim()) return;
    setCreating(true);
    try {
      await onCreateProject(newProjectName.trim());
      setNewProjectName('');
      setShowNewInput(false);
    } finally {
      setCreating(false);
    }
  };

  return (
    <aside className="w-64 h-full bg-[#f4f1ea] border-r border-[#0d0d0d] flex flex-col justify-between shrink-0 select-none">
      {/* Top Header */}
      <div className="p-4 border-b border-[#0d0d0d] space-y-3 bg-[#f7f5ef]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-[8px] bg-[#ffd184] border border-[#0d0d0d] pika-shadow flex items-center justify-center font-bold text-[#111111] text-xs font-display">
              S
            </div>
            <span className="font-display font-bold text-[#0d0d0d] text-base tracking-tight">
              Slate
            </span>
          </div>
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#ffffff] border border-[#0d0d0d] font-mono font-medium text-[#0d0d0d]">
            v0.1
          </span>
        </div>

        {/* Wireframe Button: "new project" with golden yellow primary and 2px shadow */}
        <button
          onClick={() => setShowNewInput(true)}
          className="w-full py-2.5 px-3 rounded-[14px] bg-[#ffd184] border border-[#0d0d0d] text-[#111111] font-semibold text-xs transition pika-btn flex items-center justify-center gap-1.5"
        >
          <Plus className="w-3.5 h-3.5 stroke-[2.5]" />
          <span>new project</span>
        </button>

        {showNewInput && (
          <form onSubmit={handleCreate} className="pt-1">
            <div className="flex items-center gap-1 bg-[#ffffff] border border-[#0d0d0d] rounded-[12px] p-1 pika-shadow">
              <input
                type="text"
                autoFocus
                placeholder="project-id..."
                value={newProjectName}
                onChange={(e) => setNewProjectName(e.target.value)}
                className="flex-1 bg-transparent px-2 py-0.5 text-xs text-[#0d0d0d] placeholder-slate-400 focus:outline-none font-sans font-medium"
              />
              <button
                type="submit"
                disabled={creating || !newProjectName.trim()}
                className="px-2.5 py-1 bg-[#0d0d0d] hover:bg-neutral-800 disabled:opacity-40 text-white rounded-[8px] text-[11px] font-semibold"
              >
                {creating ? <Loader2 className="w-3 h-3 animate-spin" /> : 'Save'}
              </button>
              <button
                type="button"
                onClick={() => setShowNewInput(false)}
                className="px-1.5 text-xs text-neutral-500 hover:text-black font-bold"
              >
                ✕
              </button>
            </div>
          </form>
        )}
      </div>

      {/* Projects and Chats Tree */}
      <div className="flex-1 overflow-y-auto p-3 space-y-1.5">
        <div className="px-2 py-1 text-[11px] font-bold uppercase tracking-wider text-neutral-500 font-display">
          Projects
        </div>

        {loadingProjects ? (
          <div className="flex items-center justify-center py-6 text-neutral-500 text-xs gap-2">
            <Loader2 className="w-3.5 h-3.5 animate-spin text-[#0d0d0d]" />
            <span className="font-mono text-[11px]">Loading...</span>
          </div>
        ) : projects.length === 0 ? (
          <div className="p-3 text-center text-xs text-neutral-500 font-sans">
            No projects yet.
          </div>
        ) : (
          projects.map((pId) => {
            const isActive = activeProjectId === pId;
            const isExpanded = expanded[pId] ?? isActive;
            const chats = projectChats[pId] || [];

            return (
              <div key={pId} className="space-y-0.5">
                {/* Project Row */}
                <div
                  onClick={() => onSelectProject(pId)}
                  className={`group flex items-center justify-between px-3 py-2 rounded-[14px] text-xs font-semibold transition cursor-pointer ${
                    isActive
                      ? 'bg-[#ffffff] text-[#0d0d0d] border border-[#0d0d0d] pika-shadow'
                      : 'text-neutral-700 hover:bg-[#eae6dd] hover:text-[#0d0d0d]'
                  }`}
                >
                  <div className="flex items-center gap-2 truncate flex-1 min-w-0">
                    <button
                      type="button"
                      onClick={(e) => toggleExpand(pId, e)}
                      className="p-0.5 rounded text-neutral-600 hover:text-black transition shrink-0"
                    >
                      {isExpanded ? (
                        <ChevronDown className="w-3 h-3 stroke-[2.5]" />
                      ) : (
                        <ChevronRight className="w-3 h-3 stroke-[2.5]" />
                      )}
                    </button>
                    <Folder className={`w-3.5 h-3.5 shrink-0 ${isActive ? 'text-[#0d0d0d]' : 'text-neutral-500'}`} />
                    <span className="truncate font-sans">{pId}</span>
                  </div>

                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition">
                    <button
                      type="button"
                      title="New chat in project"
                      onClick={(e) => {
                        e.stopPropagation();
                        onCreateChat(pId);
                      }}
                      className="p-1 rounded-md hover:bg-neutral-200 text-neutral-700 hover:text-black transition"
                    >
                      <Plus className="w-3 h-3 stroke-[2.5]" />
                    </button>
                    <button
                      type="button"
                      title="Delete project"
                      onClick={(e) => {
                        e.stopPropagation();
                        if (confirm(`Delete project "${pId}"?`)) {
                          onDeleteProject(pId);
                        }
                      }}
                      className="p-1 rounded-md hover:bg-rose-100 text-neutral-500 hover:text-rose-600 transition"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                </div>

                {/* Child Chats: Wireframe "-chat1, -chat2..." */}
                {isExpanded && (
                  <div className="pl-6 pr-1 py-1 space-y-1">
                    {chats.length === 0 ? (
                      <button
                        onClick={() => onCreateChat(pId)}
                        className="w-full text-left px-2 py-1 rounded-[8px] text-[11px] text-neutral-500 hover:text-black transition flex items-center gap-1 font-mono"
                      >
                        <Plus className="w-2.5 h-2.5" />
                        <span>-start chat</span>
                      </button>
                    ) : (
                      chats.map((c) => {
                        const isChatActive = isActive && activeChatId === c.chat_id;
                        return (
                          <div
                            key={c.chat_id}
                            onClick={() => onSelectChat(pId, c.chat_id)}
                            className={`flex items-center justify-between px-2.5 py-1.5 rounded-[10px] text-[11px] font-mono transition cursor-pointer ${
                              isChatActive
                                ? 'bg-[#cfc3ff] text-[#0d0d0d] font-bold border border-[#0d0d0d] pika-shadow'
                                : 'text-neutral-600 hover:bg-[#eae6dd] hover:text-black'
                            }`}
                          >
                            <div className="flex items-center gap-1.5 truncate">
                              <span>-</span>
                              <span className="truncate">
                                {c.title || 'chat'}
                              </span>
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Wireframe: "Settings" button at bottom */}
      <div className="p-3 border-t border-[#0d0d0d] bg-[#f7f5ef]">
        <button
          onClick={onOpenSettings}
          className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-[14px] text-[#0d0d0d] bg-[#ffffff] hover:bg-[#ffd184] border border-[#0d0d0d] text-xs font-semibold transition pika-btn"
        >
          <div className="flex items-center gap-2 font-display">
            <Settings className="w-3.5 h-3.5" />
            <span>Settings</span>
          </div>
          <span className="w-2 h-2 rounded-full bg-emerald-500 border border-[#0d0d0d]" />
        </button>
      </div>
    </aside>
  );
};
