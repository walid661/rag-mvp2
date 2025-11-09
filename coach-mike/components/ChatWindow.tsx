"use client";
import { useSession } from 'next-auth/react';
import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { chatApi } from '../lib/api';
import MessageItem from './MessageItem';
import SourcesPanel from './SourcesPanel';

interface SessionItem {
  id: string;
  title: string;
  createdAt: string;
}

/**
 * ChatWindow manages the main messaging interface. It fetches available chat
 * sessions, allows the user to create new sessions, displays the history of
 * messages for the selected session, and coordinates sending queries to the
 * RAG backend. Sources returned from the backend are displayed in a side
 * panel.
 */
export default function ChatWindow() {
  const { data: session } = useSession();
  const queryClient = useQueryClient();
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [input, setInput] = useState('');
  const [lastSources, setLastSources] = useState<Array<Record<string, any>>>([]);
  const [showSources, setShowSources] = useState(false);

  // Load user profile for chatApi; we fetch once and cache
  const { data: profileData } = useQuery({
    queryKey: ['profile'],
    queryFn: async () => {
      const res = await fetch('/api/profile');
      if (!res.ok) throw new Error('Failed to load profile');
      return (await res.json()).profile;
    },
  });

  // Load sessions list
  const { data: sessionsData } = useQuery({
    queryKey: ['sessions'],
    queryFn: async () => {
      const res = await fetch('/api/sessions');
      if (!res.ok) throw new Error('Failed to load sessions');
      return (await res.json()).sessions as SessionItem[];
    },
  });

  // When sessions load, select the most recent session by default
  useEffect(() => {
    if (sessionsData && sessionsData.length > 0 && !selectedSessionId) {
      setSelectedSessionId(sessionsData[0].id);
    }
  }, [sessionsData, selectedSessionId]);

  // Create new session mutation
  const createSession = useMutation({
    mutationFn: async () => {
      const res = await fetch('/api/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: 'Nouvelle session' }),
      });
      if (!res.ok) throw new Error('Erreur de création de session');
      return (await res.json()).id as string;
    },
    onSuccess: (id: string) => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
      setSelectedSessionId(id);
    },
  });

  // Load messages for selected session
  const { data: messagesData } = useQuery({
    queryKey: ['messages', selectedSessionId],
    queryFn: async () => {
      if (!selectedSessionId) return [];
      const res = await fetch(`/api/sessions/${selectedSessionId}/messages`);
      if (!res.ok) throw new Error('Failed to load messages');
      return (await res.json()).messages as Array<{ role: 'user' | 'assistant'; content: string; createdAt: string }>;
    },
    enabled: !!selectedSessionId,
  });

  const sendMutation = useMutation({
    mutationFn: async (message: string) => {
      if (!selectedSessionId) throw new Error('No session selected');
      // Append user message to DB
      await fetch(`/api/sessions/${selectedSessionId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: 'user', content: message }),
      });
      // Call RAG backend
      const answer = await chatApi(message, profileData || {});
      // Append assistant message
      await fetch(`/api/sessions/${selectedSessionId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: 'assistant', content: answer.answer }),
      });
      setLastSources(answer.sources);
      return answer;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['messages', selectedSessionId] });
      setInput('');
      setShowSources(true);
    },
    onError: (error: any) => {
      alert(error?.message || 'Erreur lors de l\'envoi');
    },
  });

  const handleSend = async () => {
    const trimmed = input.trim();
    if (!trimmed) return;
    sendMutation.mutate(trimmed);
  };

  if (!session) return <p className="p-4">Chargement…</p>;

  return (
    <div className="flex h-[calc(100vh-60px)]">
      {/* Sessions sidebar */}
      <aside className="w-64 border-r bg-white p-4 overflow-y-auto hidden md:block">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold">Sessions</h2>
          <button
            onClick={() => createSession.mutate()}
            className="text-sm bg-indigo-600 text-white px-2 py-1 rounded hover:bg-indigo-700"
          >
            + Nouvelle
          </button>
        </div>
        <ul className="space-y-2">
          {sessionsData?.map((s) => (
            <li key={s.id}>
              <button
                className={`w-full text-left px-2 py-1 rounded-md ${
                  s.id === selectedSessionId ? 'bg-indigo-100 font-semibold' : 'hover:bg-gray-100'
                }`}
                onClick={() => setSelectedSessionId(s.id)}
              >
                {s.title || 'Sans titre'}
              </button>
            </li>
          ))}
        </ul>
      </aside>
      {/* Main chat area */}
      <main className="flex-1 flex flex-col bg-gray-50">
        <div className="flex-1 overflow-y-auto p-4">
          {messagesData?.length ? (
            messagesData.map((m, idx) => <MessageItem key={idx} role={m.role} content={m.content} />)
          ) : (
            <p className="text-center text-gray-500 mt-10">Commencez la conversation !</p>
          )}
        </div>
        <div className="p-4 border-t bg-white">
          <div className="flex space-x-2 mb-2">
            {/* Quick suggestions */}
            {['Plan hebdomadaire', 'Séance 30 min', 'Full body'].map((suggest) => (
              <button
                key={suggest}
                onClick={() => setInput(suggest)}
                className="px-2 py-1 bg-gray-200 rounded-md text-sm hover:bg-gray-300"
              >
                {suggest}
              </button>
            ))}
          </div>
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              disabled={sendMutation.isPending || !selectedSessionId}
              className="flex-1 p-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="Tapez votre message..."
            />
            <button
              onClick={handleSend}
              disabled={sendMutation.isPending || !selectedSessionId}
              className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
            >
              Envoyer
            </button>
            {lastSources.length > 0 && (
              <button
                onClick={() => setShowSources((p) => !p)}
                className="px-3 py-2 bg-gray-200 rounded-md text-sm hover:bg-gray-300"
              >
                {showSources ? 'Masquer sources' : 'Voir sources'}
              </button>
            )}
          </div>
        </div>
      </main>
      {showSources && (
        <SourcesPanel sources={lastSources} onClose={() => setShowSources(false)} />
      )}
    </div>
  );
}