import { prisma } from '../prisma';
import type { UserProfile } from '../types';

export interface ProfileStore {
  get(uid: string): Promise<UserProfile | null>;
  upsert(uid: string, profile: UserProfile): Promise<void>;
}

export interface ChatStore {
  createSession(uid: string, title?: string): Promise<string>;
  listSessions(uid: string): Promise<Array<{ id: string; title: string; createdAt: string }>>;
  appendMessage(sessionId: string, role: 'user' | 'assistant', content: string): Promise<void>;
  listMessages(sessionId: string): Promise<Array<{ role: string; content: string; createdAt: string }>>;
}

/**
 * Prisma-backed implementation of ProfileStore.
 */
export class PrismaProfileStore implements ProfileStore {
  async get(uid: string): Promise<UserProfile | null> {
    const record = await prisma.profile.findUnique({ where: { userId: uid } });
    if (!record) return null;
    // Deserialize JSON string to object (SQLite compatibility)
    try {
      return JSON.parse(record.data) as UserProfile;
    } catch (e) {
      console.error(`Failed to parse profile data for user ${uid}:`, e);
      return null;
    }
  }

  async upsert(uid: string, profile: UserProfile): Promise<void> {
    // Serialize object to JSON string (SQLite compatibility)
    const dataJson = JSON.stringify(profile);
    await prisma.profile.upsert({
      where: { userId: uid },
      update: { data: dataJson },
      create: { userId: uid, data: dataJson }
    });
  }
}

/**
 * Prisma-backed implementation of ChatStore.
 */
export class PrismaChatStore implements ChatStore {
  async createSession(uid: string, title?: string): Promise<string> {
    const session = await prisma.chatSession.create({
      data: {
        userId: uid,
        title: title || new Date().toLocaleString(),
      },
    });
    return session.id;
  }

  async listSessions(uid: string): Promise<Array<{ id: string; title: string; createdAt: string }>> {
    const sessions = await prisma.chatSession.findMany({
      where: { userId: uid },
      orderBy: { createdAt: 'desc' },
      select: { id: true, title: true, createdAt: true },
    });
    return sessions.map((s) => ({ id: s.id, title: s.title, createdAt: s.createdAt.toISOString() }));
  }

  async appendMessage(sessionId: string, role: 'user' | 'assistant', content: string): Promise<void> {
    await prisma.message.create({ data: { sessionId, role, content } });
  }

  async listMessages(sessionId: string): Promise<Array<{ role: string; content: string; createdAt: string }>> {
    const messages = await prisma.message.findMany({
      where: { sessionId },
      orderBy: { createdAt: 'asc' },
      select: { role: true, content: true, createdAt: true },
    });
    return messages.map((m) => ({ role: m.role, content: m.content, createdAt: m.createdAt.toISOString() }));
  }
}