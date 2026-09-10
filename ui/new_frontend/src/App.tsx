import { useState, useEffect, useCallback } from 'react';
import { SidebarLeft } from './components/SidebarLeft';
import { SidebarRight } from './components/SidebarRight';
import { ChatArea } from './components/ChatArea';
import { EmptyState } from './components/EmptyState';
import { SettingsModal } from './components/SettingsModal';
import { AddDocumentModal } from './components/AddDocumentModal';
import { ProjectInstructionsModal } from './components/ProjectInstructionsModal';
import { api } from './services/api';
import type { Chat, DocumentItem, Message, ProjectStats } from './types';

export default function App() {
  const [projects, setProjects] = useState<string[]>([]);
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);

  const [projectChats, setProjectChats] = useState<Record<string, Chat[]>>({});
  const [messages, setMessages] = useState<Message[]>([]);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [sendingQuery, setSendingQuery] = useState(false);

  const [stats, setStats] = useState<ProjectStats | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loadingDocuments, setLoadingDocuments] = useState(false);

  const [rightSidebarOpen, setRightSidebarOpen] = useState(true);

  // Modals
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isAddDocOpen, setIsAddDocOpen] = useState(false);
  const [isInstructionsOpen, setIsInstructionsOpen] = useState(false);

  // Toast / notification
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  const showToast = (message: string, type: 'success' | 'error' = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  // Load all projects
  const fetchProjects = useCallback(async () => {
    setLoadingProjects(true);
    try {
      const list = await api.listProjects();
      setProjects(list);

      // Preload chats for all projects
      for (const pId of list) {
        try {
          const chats = await api.listChats(pId);
          setProjectChats((prev) => ({ ...prev, [pId]: chats }));
        } catch {
          // ignore chat load error for individual project
        }
      }

      // If activeProjectId is not in list, fallback
      if (activeProjectId && !list.includes(activeProjectId)) {
        setActiveProjectId(list.length > 0 ? list[0] : null);
      }
    } catch (err: any) {
      console.error('Failed to load projects:', err);
    } finally {
      setLoadingProjects(false);
    }
  }, [activeProjectId]);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  // Load chats for a given project
  const fetchChatsForProject = async (pId: string) => {
    try {
      const chats = await api.listChats(pId);
      setProjectChats((prev) => ({ ...prev, [pId]: chats }));
      return chats;
    } catch {
      return [];
    }
  };

  // Load messages when active chat or active project changes
  const fetchMessages = useCallback(async (pId: string, cId: string) => {
    setLoadingMessages(true);
    try {
      const msgs = await api.getMessages(pId, cId);
      setMessages(msgs);
    } catch (err: any) {
      console.error('Failed to load messages:', err);
      setMessages([]);
    } finally {
      setLoadingMessages(false);
    }
  }, []);

  // Load stats and documents for active project
  const fetchProjectDetails = useCallback(async (pId: string) => {
    setLoadingDocuments(true);
    try {
      const [st, docs] = await Promise.all([
        api.getProjectStats(pId).catch(() => ({ project_id: pId, total_chunks: 0 })),
        api.listDocuments(pId).catch(() => []),
      ]);
      setStats(st);
      setDocuments(docs);
    } finally {
      setLoadingDocuments(false);
    }
  }, []);

  useEffect(() => {
    if (activeProjectId) {
      fetchProjectDetails(activeProjectId);
      if (activeChatId) {
        fetchMessages(activeProjectId, activeChatId);
      } else {
        setMessages([]);
      }
    } else {
      setStats(null);
      setDocuments([]);
      setMessages([]);
    }
  }, [activeProjectId, activeChatId, fetchProjectDetails, fetchMessages]);

  // Handle project selection
  const handleSelectProject = async (pId: string) => {
    setActiveProjectId(pId);
    let chats = projectChats[pId];
    if (!chats) {
      chats = await fetchChatsForProject(pId);
    }
    if (chats && chats.length > 0) {
      setActiveChatId(chats[0].chat_id);
    } else {
      // Create initial chat if none exists
      try {
        const newChat = await api.createChat(pId, 'chat1');
        setProjectChats((prev) => ({ ...prev, [pId]: [newChat] }));
        setActiveChatId(newChat.chat_id);
      } catch {
        setActiveChatId(null);
      }
    }
  };

  // Handle chat selection
  const handleSelectChat = (pId: string, cId: string) => {
    setActiveProjectId(pId);
    setActiveChatId(cId);
  };

  // Create Project
  const handleCreateProject = async (name: string) => {
    try {
      await api.createProject(name);
      showToast(`Project "${name}" created!`);
      await fetchProjects();
      await handleSelectProject(name);
    } catch (err: any) {
      showToast(err.message || 'Failed to create project', 'error');
    }
  };

  // Delete Project
  const handleDeleteProject = async (pId: string) => {
    try {
      await api.deleteProject(pId);
      showToast(`Project "${pId}" deleted`);
      if (activeProjectId === pId) {
        setActiveProjectId(null);
        setActiveChatId(null);
      }
      await fetchProjects();
    } catch (err: any) {
      showToast(err.message || 'Failed to delete project', 'error');
    }
  };

  // Create new chat in project
  const handleCreateChat = async (pId: string) => {
    try {
      const existing = projectChats[pId] || [];
      const title = `chat${existing.length + 1}`;
      const newChat = await api.createChat(pId, title);
      setProjectChats((prev) => ({
        ...prev,
        [pId]: [...(prev[pId] || []), newChat],
      }));
      setActiveProjectId(pId);
      setActiveChatId(newChat.chat_id);
      showToast(`New chat "${title}" created`);
    } catch (err: any) {
      showToast(err.message || 'Failed to create chat', 'error');
    }
  };

  // Send message
  const handleSendMessage = async (text: string) => {
    if (!activeProjectId) return;

    let cId = activeChatId;
    if (!cId) {
      try {
        const newChat = await api.createChat(activeProjectId, 'chat1');
        cId = newChat.chat_id;
        setActiveChatId(cId);
        setProjectChats((prev) => ({
          ...prev,
          [activeProjectId]: [...(prev[activeProjectId] || []), newChat],
        }));
      } catch (err: any) {
        showToast(err.message || 'Could not initiate chat', 'error');
        return;
      }
    }

    // Optimistically append user message
    const tempUserMsg: Message = {
      role: 'user',
      content: text,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);
    setSendingQuery(true);

    try {
      const response = await api.queryProject(activeProjectId, {
        query: text,
        chat_id: cId,
        grade_response: true,
      });

      const assistantMsg: Message = {
        role: 'assistant',
        content: response.answer,
        citations: response.citations,
        grade: response.grade,
        created_at: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, assistantMsg]);
      // Refresh documents and stats
      fetchProjectDetails(activeProjectId);
    } catch (err: any) {
      showToast(err.message || 'Failed to generate answer', 'error');
    } finally {
      setSendingQuery(false);
    }
  };

  // Handlers for Screen 1 ("before making any project")
  const handleEmptyNewProject = async (name?: string) => {
    const pName = name || `project${projects.length + 1}`;
    await handleCreateProject(pName);
  };

  const handleEmptyAsk = async (question: string) => {
    let targetProject = activeProjectId || (projects.length > 0 ? projects[0] : 'default_project');
    if (!projects.includes(targetProject)) {
      await handleCreateProject(targetProject);
    } else {
      setActiveProjectId(targetProject);
    }
    await handleSendMessage(question);
  };

  const handleEmptyAddDocuments = async () => {
    let targetProject = activeProjectId || (projects.length > 0 ? projects[0] : 'default_project');
    if (!projects.includes(targetProject)) {
      await handleCreateProject(targetProject);
    } else {
      setActiveProjectId(targetProject);
    }
    setIsAddDocOpen(true);
  };

  return (
    <div className="flex h-screen w-screen bg-[#fcfaf7] text-[#0d0d0d] overflow-hidden font-sans">
      {/* Toast notification with DESIGN.md tokens */}
      {toast && (
        <div
          className={`fixed top-4 right-4 z-50 px-4 py-2.5 rounded-[14px] text-xs font-mono font-bold border border-[#0d0d0d] pika-shadow-lg transition-all ${
            toast.type === 'error'
              ? 'bg-rose-100 text-rose-900'
              : 'bg-[#ffd184] text-[#111111]'
          }`}
        >
          {toast.message}
        </div>
      )}

      {/* Left Sidebar (Wireframe Screen 2 Left) */}
      <SidebarLeft
        projects={projects}
        activeProjectId={activeProjectId}
        activeChatId={activeChatId}
        projectChats={projectChats}
        loadingProjects={loadingProjects}
        onSelectProject={handleSelectProject}
        onSelectChat={handleSelectChat}
        onCreateProject={handleCreateProject}
        onDeleteProject={handleDeleteProject}
        onCreateChat={handleCreateChat}
        onOpenSettings={() => setIsSettingsOpen(true)}
      />

      {/* Center View: Wireframe Screen 1 (Empty state) or Screen 2 (Chat interface) */}
      {!activeProjectId ? (
        <EmptyState
          onNewProject={handleEmptyNewProject}
          onAsk={handleEmptyAsk}
          onAddDocuments={handleEmptyAddDocuments}
        />
      ) : (
        <ChatArea
          projectId={activeProjectId}
          chatId={activeChatId}
          messages={messages}
          loadingMessages={loadingMessages}
          sendingQuery={sendingQuery}
          onSendMessage={handleSendMessage}
          onToggleRightSidebar={() => setRightSidebarOpen(!rightSidebarOpen)}
          rightSidebarOpen={rightSidebarOpen}
        />
      )}

      {/* Right Sidebar (Wireframe Screen 2 Right: "Project specific settings") */}
      {activeProjectId && rightSidebarOpen && (
        <SidebarRight
          projectId={activeProjectId}
          stats={stats}
          documents={documents}
          loadingDocuments={loadingDocuments}
          onOpenAddDocument={() => setIsAddDocOpen(true)}
          onOpenInstructions={() => setIsInstructionsOpen(true)}
        />
      )}

      {/* Modals */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        onRefreshProjects={fetchProjects}
      />

      {activeProjectId && (
        <>
          <AddDocumentModal
            isOpen={isAddDocOpen}
            projectId={activeProjectId}
            onClose={() => setIsAddDocOpen(false)}
            onDocumentAdded={() => fetchProjectDetails(activeProjectId)}
          />

          <ProjectInstructionsModal
            isOpen={isInstructionsOpen}
            projectId={activeProjectId}
            onClose={() => setIsInstructionsOpen(false)}
          />
        </>
      )}
    </div>
  );
}
