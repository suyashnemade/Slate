import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, FileText, ChevronDown, ChevronUp, Loader2, Sparkles, CheckCircle2, AlertCircle } from 'lucide-react';
import type { Message, Citation } from '../types';

interface ChatAreaProps {
  projectId: string;
  chatId: string | null;
  messages: Message[];
  loadingMessages: boolean;
  sendingQuery: boolean;
  onSendMessage: (text: string) => Promise<void>;
  onToggleRightSidebar?: () => void;
  rightSidebarOpen?: boolean;
}

export const ChatArea: React.FC<ChatAreaProps> = ({
  projectId,
  chatId,
  messages,
  loadingMessages,
  sendingQuery,
  onSendMessage,
  onToggleRightSidebar,
  rightSidebarOpen = true,
}) => {
  const [input, setInput] = useState('');
  const [activeCitationIdx, setActiveCitationIdx] = useState<Record<string, number | null>>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, sendingQuery]);

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!input.trim() || sendingQuery) return;
    const text = input.trim();
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
    await onSendMessage(text);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const toggleCitation = (msgKey: string, idx: number) => {
    setActiveCitationIdx((prev) => ({
      ...prev,
      [msgKey]: prev[msgKey] === idx ? null : idx,
    }));
  };

  return (
    <main className="flex-1 h-full flex flex-col bg-[#fcfaf7] overflow-hidden relative">
      {/* Top Header */}
      <header className="h-14 px-6 border-b border-[#0d0d0d] flex items-center justify-between bg-[#f7f5ef] z-10 select-none">
        <div className="flex items-center gap-2 text-xs font-mono">
          <span className="font-bold text-[#0d0d0d] px-2 py-0.5 rounded-[6px] bg-[#ffd184] border border-[#0d0d0d]">
            {projectId}
          </span>
          <span className="text-neutral-400">/</span>
          <span className="text-neutral-600 font-medium">
            {chatId || 'chat'}
          </span>
        </div>

        {onToggleRightSidebar && (
          <button
            onClick={onToggleRightSidebar}
            className={`text-xs px-3 py-1.5 rounded-[10px] border border-[#0d0d0d] font-semibold transition pika-btn ${
              rightSidebarOpen
                ? 'bg-[#ffffff] text-[#0d0d0d]'
                : 'bg-[#ffd184] text-[#111111]'
            }`}
          >
            {rightSidebarOpen ? 'Hide settings' : 'Project settings'}
          </button>
        )}
      </header>

      {/* Messages Stream */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
        {loadingMessages ? (
          <div className="h-full flex flex-col items-center justify-center text-neutral-500 text-xs gap-2">
            <Loader2 className="w-4 h-4 animate-spin text-[#0d0d0d]" />
            <span className="font-mono">Loading conversation...</span>
          </div>
        ) : messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-3 max-w-md mx-auto">
            <div className="w-12 h-12 rounded-[16px] bg-[#ffd184] border border-[#0d0d0d] pika-shadow flex items-center justify-center text-[#111111]">
              <Sparkles className="w-6 h-6 stroke-[2]" />
            </div>
            <h2 className="text-lg font-display font-bold text-[#0d0d0d]">
              {projectId} is ready
            </h2>
            <p className="text-xs text-neutral-600 leading-relaxed font-sans">
              Type your inquiry below in the chat window. Slate performs hybrid vector retrieval, analyzes context, and responds with verified citations.
            </p>
          </div>
        ) : (
          messages.map((msg, idx) => {
            const isUser = msg.role === 'user';
            const msgKey = `msg-${idx}`;
            const activeCit = activeCitationIdx[msgKey] ?? null;

            return (
              <div
                key={msgKey}
                className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}
              >
                {!isUser && (
                  <div className="w-8 h-8 rounded-[10px] bg-[#ffd184] border border-[#0d0d0d] pika-shadow flex items-center justify-center text-[#111111] shrink-0 mt-0.5 font-bold text-xs">
                    <Bot className="w-4 h-4 stroke-[2.5]" />
                  </div>
                )}

                <div
                  className={`max-w-2xl text-sm leading-relaxed ${
                    isUser
                      ? 'bg-[#cfc3ff] text-[#0d0d0d] border border-[#0d0d0d] pika-shadow rounded-[18px] rounded-br-[4px] px-4 py-3 font-medium'
                      : 'bg-[#ffffff] text-[#0d0d0d] border border-[#0d0d0d] pika-shadow rounded-[18px] rounded-bl-[4px] p-5 space-y-3 font-sans'
                  }`}
                >
                  {/* Message Content */}
                  <div className="whitespace-pre-wrap">{msg.content}</div>

                  {/* Wireframe: "Response with citation" */}
                  {!isUser && msg.citations && msg.citations.length > 0 && (
                    <div className="pt-3 border-t border-neutral-200 space-y-2">
                      <div className="text-[11px] font-display font-bold uppercase tracking-wider text-neutral-600 flex items-center gap-1.5">
                        <FileText className="w-3.5 h-3.5 text-[#0d0d0d]" />
                        <span>Sources & Citations ({msg.citations.length})</span>
                      </div>

                      {/* Horizontal citation pills */}
                      <div className="flex flex-wrap gap-1.5">
                        {msg.citations.map((c: Citation, cIdx: number) => {
                          const label = c.filename || c.source || `Doc ${cIdx + 1}`;
                          const isSelected = activeCit === cIdx;
                          return (
                            <button
                              key={`cit-pill-${cIdx}`}
                              type="button"
                              onClick={() => toggleCitation(msgKey, cIdx)}
                              className={`px-2.5 py-1 rounded-[10px] text-[11px] font-mono transition flex items-center gap-1.5 border border-[#0d0d0d] ${
                                isSelected
                                  ? 'bg-[#ffd184] text-[#111111] font-bold pika-shadow'
                                  : 'bg-[#fcfaf7] text-neutral-700 hover:bg-[#fff9ee]'
                              }`}
                            >
                              <span className="font-bold">[{cIdx + 1}]</span>
                              <span className="truncate max-w-[150px]">{label}</span>
                              {isSelected ? (
                                <ChevronUp className="w-3 h-3 stroke-[2.5]" />
                              ) : (
                                <ChevronDown className="w-3 h-3 stroke-[2.5]" />
                              )}
                            </button>
                          );
                        })}
                      </div>

                      {/* Selected Citation Snippet View */}
                      {activeCit !== null && msg.citations[activeCit] && (
                        <div className="p-3.5 rounded-[14px] bg-[#fcfaf7] border border-[#0d0d0d] space-y-1.5 text-xs">
                          <div className="flex items-center justify-between text-[#0d0d0d] font-mono text-[11px]">
                            <span className="font-bold">
                              Source [{activeCit + 1}]: {msg.citations[activeCit].filename || msg.citations[activeCit].source || 'Document'}
                            </span>
                            {msg.citations[activeCit].similarity_score !== undefined && (
                              <span className="px-1.5 py-0.5 rounded bg-[#ffffff] border border-[#0d0d0d] font-semibold text-[10px]">
                                Score: {(msg.citations[activeCit].similarity_score! * 100).toFixed(0)}%
                              </span>
                            )}
                          </div>
                          {msg.citations[activeCit].content && (
                            <p className="text-neutral-700 font-serif italic text-xs leading-relaxed border-l-2 border-[#0d0d0d] pl-3 py-0.5 bg-[#ffffff] p-2 rounded-[8px]">
                              "{msg.citations[activeCit].content}"
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Quality Verification Badge */}
                  {!isUser && msg.grade && (
                    <div className="flex items-center gap-1.5 pt-1 text-[11px] text-neutral-600 font-mono">
                      {msg.grade.passed ? (
                        <span className="text-emerald-700 flex items-center gap-1 font-semibold">
                          <CheckCircle2 className="w-3.5 h-3.5 stroke-[2.5]" />
                          <span>Quality Verified ({(msg.grade.score! * 100).toFixed(0)}%)</span>
                        </span>
                      ) : (
                        <span className="text-amber-700 flex items-center gap-1 font-semibold">
                          <AlertCircle className="w-3.5 h-3.5 stroke-[2.5]" />
                          <span>Low Confidence</span>
                        </span>
                      )}
                      {msg.grade.feedback && (
                        <span className="text-neutral-500 truncate">· {msg.grade.feedback}</span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}

        {/* Loading Spinner during Active Query */}
        {sendingQuery && (
          <div className="flex gap-3 justify-start items-center text-xs">
            <div className="w-8 h-8 rounded-[10px] bg-[#ffd184] border border-[#0d0d0d] pika-shadow flex items-center justify-center text-[#111111] shrink-0">
              <Loader2 className="w-4 h-4 animate-spin stroke-[2.5]" />
            </div>
            <div className="bg-[#ffffff] border border-[#0d0d0d] pika-shadow rounded-[16px] px-4 py-3 text-[#0d0d0d] flex items-center gap-2 font-medium">
              <Sparkles className="w-4 h-4 text-[#ffd184] fill-[#ffd184] stroke-[#0d0d0d]" />
              <span>Searching knowledge graph and generating answer with citations...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Wireframe Element: "Chat window" */}
      <footer className="p-4 bg-[#f7f5ef] border-t border-[#0d0d0d]">
        <form
          onSubmit={handleSubmit}
          className="max-w-3xl mx-auto relative flex items-center bg-[#ffffff] border border-[#0d0d0d] rounded-[20px] px-4 py-2 pika-shadow-lg transition"
        >
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={(e) => {
              setInput(e.target.value);
              e.target.style.height = 'auto';
              e.target.style.height = `${Math.min(e.target.scrollHeight, 140)}px`;
            }}
            onKeyDown={handleKeyDown}
            placeholder="Chat window — Ask a question about your project documents..."
            className="flex-1 bg-transparent px-1 py-1 text-sm text-[#0d0d0d] placeholder-neutral-400 resize-none focus:outline-none max-h-36 font-sans font-medium leading-relaxed"
          />

          <button
            type="submit"
            disabled={!input.trim() || sendingQuery}
            className="p-2.5 rounded-[14px] bg-[#ffd184] border border-[#0d0d0d] hover:bg-[#ffc666] disabled:opacity-30 text-[#111111] transition flex items-center justify-center shrink-0 ml-2 pika-btn"
          >
            {sendingQuery ? (
              <Loader2 className="w-4 h-4 animate-spin stroke-[2.5]" />
            ) : (
              <Send className="w-4 h-4 stroke-[2.5]" />
            )}
          </button>
        </form>
        <div className="text-[10px] text-neutral-500 text-center mt-1.5 font-mono">
          Press Enter to send · Shift+Enter for new line
        </div>
      </footer>
    </main>
  );
};
