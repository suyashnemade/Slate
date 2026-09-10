import React, { useState } from 'react';
import { BookOpen, X, Check } from 'lucide-react';

interface ProjectInstructionsModalProps {
  isOpen: boolean;
  projectId: string;
  onClose: () => void;
}

export const ProjectInstructionsModal: React.FC<ProjectInstructionsModalProps> = ({
  isOpen,
  projectId,
  onClose,
}) => {
  const storageKey = `slate_instructions_${projectId}`;
  const [instructions, setInstructions] = useState(() => {
    return (
      localStorage.getItem(storageKey) ||
      `You are Slate Assistant for project "${projectId}". Provide accurate responses with citations to ingested documents whenever possible.`
    );
  });
  const [saved, setSaved] = useState(false);

  if (!isOpen) return null;

  const handleSave = () => {
    localStorage.setItem(storageKey, instructions);
    setSaved(true);
    setTimeout(() => {
      setSaved(false);
      onClose();
    }, 700);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#0d0d0d]/50 backdrop-blur-xs p-4">
      <div className="w-full max-w-lg rounded-[24px] bg-[#ffffff] border border-[#0d0d0d] p-6 sm:p-7 pika-shadow-lg text-[#0d0d0d]">
        <div className="flex items-center justify-between pb-4 border-b border-[#0d0d0d]">
          <div className="flex items-center gap-2 font-display font-bold text-base text-[#0d0d0d]">
            <BookOpen className="w-5 h-5 text-[#0d0d0d]" />
            <span>Project Instructions —</span>
            <span className="font-mono text-xs px-2 py-0.5 rounded-[6px] bg-[#ffd184] border border-[#0d0d0d]">{projectId}</span>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-[8px] text-neutral-500 hover:text-black hover:bg-neutral-100 transition"
          >
            <X className="w-4 h-4 stroke-[2.5]" />
          </button>
        </div>

        <div className="mt-4 space-y-3">
          <p className="text-xs text-neutral-600 leading-relaxed font-sans">
            Specify customized domain instructions, answering persona, or reasoning rules for this project workspace.
          </p>
          <textarea
            rows={7}
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
            className="w-full px-4 py-3 text-xs rounded-[16px] bg-[#fcfaf7] border border-[#0d0d0d] text-[#0d0d0d] focus:outline-none focus:ring-1 focus:ring-[#0d0d0d] font-mono leading-relaxed resize-none"
          />
        </div>

        <div className="mt-5 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold text-neutral-600 hover:text-black transition"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSave}
            className="px-5 py-2.5 bg-[#ffd184] border border-[#0d0d0d] hover:bg-[#ffc666] text-[#111111] rounded-[14px] text-xs font-display font-bold transition pika-btn flex items-center gap-1.5"
          >
            {saved ? (
              <>
                <Check className="w-4 h-4 text-[#0d0d0d] stroke-[3]" />
                <span>Saved!</span>
              </>
            ) : (
              <span>Save Instructions</span>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
