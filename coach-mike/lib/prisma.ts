import { PrismaClient } from '@prisma/client';

// Prevent instantiating multiple Prisma clients in development with hot reload.
// See https://www.prisma.io/docs/guides/performance-and-optimization/connection-management#preventing-hot-reload-from-creating-new-instances
declare global {
  // eslint-disable-next-line no-var
  var prisma: PrismaClient | undefined;
}

const prismaClient = global.prisma || new PrismaClient();

if (process.env.NODE_ENV !== 'production') {
  global.prisma = prismaClient;
}

export const prisma = prismaClient;