import React, { useState } from 'react';
import { Plus, Search, UploadCloud, ArrowRight, FolderPlus } from 'lucide-react';

interface EmptyStateProps {
  onNewProject: (name?: string) => void;
  onAsk: (question: string) => void;
  onAddDocuments: () => void;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  onNewProject,
  onAsk,
  onAddDocuments,
}) => {
  const [askQuery, setAskQuery] = useState('');
  const [projectName, setProjectName] = useState('');
  const [isCreatingProject, setIsCreatingProject] = useState(false);

  const handleAskSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!askQuery.trim()) return;
    onAsk(askQuery.trim());
  };

  const handleProjectSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectName.trim()) return;
    onNewProject(projectName.trim());
    setProjectName('');
    setIsCreatingProject(false);
  };

  return (
    <div className="flex-1 h-full flex flex-col items-center justify-center p-6 lg:p-12 overflow-y-auto bg-[#fcfaf7]">
      <div className="w-full max-w-xl space-y-6">
        {/* Editorial Heading */}
        <div className="text-center space-y-2">
          <h1 className="text-3xl sm:text-4xl font-display font-extrabold tracking-tight text-[#0d0d0d]">
            Slate Workspace
          </h1>
          <p className="text-sm text-neutral-600 max-w-md mx-auto leading-relaxed">
            Multimodal knowledge exploration and agentic synthesis. Index your library, inspect evidence, and query across projects.
          </p>
        </div>

        {/* Wireframe Centered Frame (project/image.png: Screen 1) */}
        <div className="bg-[#ffffff] border border-[#0d0d0d] rounded-[24px] p-6 sm:p-8 space-y-5 pika-shadow-lg">
          
          {/* Wireframe Element 1: "new project" in radiant golden-yellow */}
          {!isCreatingProject ? (
            <button
              onClick={() => setIsCreatingProject(true)}
              className="w-full py-3.5 px-4 rounded-[18px] bg-[#ffd184] border border-[#0d0d0d] text-[#111111] font-display font-bold text-sm tracking-wide transition pika-btn flex items-center justify-center gap-2"
            >
              <Plus className="w-4 h-4 stroke-[3]" />
              <span>new project</span>
            </button>
          ) : (
            <form onSubmit={handleProjectSubmit} className="space-y-2">
              <div className="flex items-center gap-2 bg-[#fcfaf7] border border-[#0d0d0d] rounded-[16px] p-2 pika-shadow">
                <FolderPlus className="w-4 h-4 text-[#0d0d0d] ml-1 shrink-0" />
                <input
                  type="text"
                  autoFocus
                  placeholder="Enter project identifier..."
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  className="flex-1 bg-transparent px-2 py-1 text-sm text-[#0d0d0d] placeholder-neutral-400 focus:outline-none font-sans font-medium"
                />
                <button
                  type="submit"
                  disabled={!projectName.trim()}
                  className="px-3.5 py-1.5 bg-[#0d0d0d] hover:bg-neutral-800 disabled:opacity-40 text-white rounded-[12px] text-xs font-bold font-display transition"
                >
                  Create
                </button>
                <button
                  type="button"
                  onClick={() => setIsCreatingProject(false)}
                  className="px-2 py-1 text-xs text-neutral-500 hover:text-black font-semibold"
                >
                  Cancel
                </button>
              </div>
            </form>
          )}

          {/* Wireframe Element 2: "ASK" */}
          <form onSubmit={handleAskSubmit} className="relative">
            <div className="relative flex items-center">
              <Search className="w-4 h-4 text-neutral-500 absolute left-4 pointer-events-none" />
              <input
                type="text"
                value={askQuery}
                onChange={(e) => setAskQuery(e.target.value)}
                placeholder="ASK — Search across documents or ask a question..."
                className="w-full py-3.5 pl-11 pr-12 rounded-[18px] bg-[#fcfaf7] border border-[#0d0d0d] text-[#0d0d0d] placeholder-neutral-400 text-sm focus:outline-none focus:ring-1 focus:ring-[#0d0d0d] transition font-sans font-medium"
              />
              <button
                type="submit"
                disabled={!askQuery.trim()}
                className="absolute right-2 p-2 rounded-[12px] bg-[#ffd184] border border-[#0d0d0d] hover:bg-[#ffc666] disabled:opacity-30 text-[#111111] transition pika-btn"
              >
                <ArrowRight className="w-4 h-4 stroke-[2.5]" />
              </button>
            </div>
          </form>

          {/* Wireframe Element 3: "ADD DOCUMENTS" */}
          <button
            onClick={onAddDocuments}
            className="w-full py-4 px-4 rounded-[18px] border-2 border-dashed border-[#0d0d0d] hover:bg-[#fff9ef] text-[#0d0d0d] transition group flex flex-col items-center justify-center gap-1 text-center"
          >
            <UploadCloud className="w-6 h-6 text-[#0d0d0d] group-hover:scale-110 transition-transform" />
            <span className="text-xs font-display font-extrabold tracking-wider uppercase text-[#0d0d0d]">
              ADD DOCUMENTS
            </span>
            <span className="text-[11px] text-neutral-500 font-sans">
              Drop PDFs, Markdown, TXT, or paste research notes
            </span>
          </button>
        </div>
      </div>
    </div>
  );
};
