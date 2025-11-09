import { PrismaProfileStore, PrismaChatStore } from './sql';

// In future, additional stores (e.g. Firestore) can be added here. For now we
// choose Prisma (Option A) as the simplest and most reliable default.

export const profileStore = new PrismaProfileStore();
export const chatStore = new PrismaChatStore();