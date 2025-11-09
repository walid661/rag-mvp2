import { NextAuthOptions } from 'next-auth';
import CredentialsProvider from 'next-auth/providers/credentials';
import { prisma } from './prisma';

/**
 * NextAuth configuration for the Coach Mike application.
 *
 * We use a very simple Credentials provider that accepts a single
 * username field. When a user signs in we either find an existing
 * User record or create a new one. The user's ID is persisted in
 * JWT sessions so we can associate chat history and profiles. In a
 * production environment you should replace this with a more robust
 * authentication mechanism (e.g. email/password or OAuth).
 */
export const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      name: 'Username',
      credentials: {
        username: { label: 'Username', type: 'text', placeholder: 'Enter a username' },
      },
      async authorize(credentials) {
        const username = credentials?.username?.trim();
        if (!username) return null;
        // Find user by name or create a new one
        let user = await prisma.user.findFirst({ where: { name: username } });
        if (!user) {
          user = await prisma.user.create({ data: { name: username } });
        }
        return { id: user.id, name: user.name ?? undefined };
      },
    }),
  ],
  session: {
    strategy: 'jwt',
  },
  pages: {
    signIn: '/login',
  },
  callbacks: {
    async session({ session, token }) {
      if (session.user && token.sub) {
        // Attach the user id to the session object
        // so we can access it in client components
        // Type casting due to NextAuth's loose session type
        (session.user as any).id = token.sub;
      }
      return session;
    },
  },
  secret: process.env.NEXTAUTH_SECRET,
};