import type { UserProfile, ChatResponse } from './types';

/**
 * chatApi sends a user query along with their profile to the backend API. This
 * helper automatically proxies through the Next.js route at `/api/chat` to
 * protect any secret API keys on the server. On success it returns the
 * generated answer and any accompanying sources.
 */
export async function chatApi(query: string, profile: UserProfile): Promise<ChatResponse> {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, profile }),
  });
  if (!res.ok) {
    throw new Error(await res.text());
  }
  return (await res.json()) as ChatResponse;
}