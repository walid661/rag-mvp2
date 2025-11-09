import NextAuth from 'next-auth';
import { authOptions } from '../../../../lib/auth';

// Create an auth handler instance using the shared authOptions.
const handler = NextAuth(authOptions);

export { handler as GET, handler as POST };