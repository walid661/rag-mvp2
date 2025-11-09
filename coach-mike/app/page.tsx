import { getServerSession } from 'next-auth';
import { redirect } from 'next/navigation';
import { authOptions } from '../lib/auth';

export default async function HomePage() {
  const session = await getServerSession(authOptions);
  if (!session) {
    return redirect('/login');
  }
  // Authenticated users are sent to the chat interface. The chat page will
  // handle onboarding if necessary.
  return redirect('/chat');
}