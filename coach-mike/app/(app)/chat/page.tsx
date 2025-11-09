import { getServerSession } from 'next-auth';
import { redirect } from 'next/navigation';
import { authOptions } from '../../../lib/auth';
import { profileStore } from '../../../lib/store';
import ChatWindow from '../../../components/ChatWindow';

export default async function ChatPage() {
  const session = await getServerSession(authOptions);
  if (!session || !(session.user as any)?.id) {
    return redirect('/login');
  }
  const uid = (session.user as any).id as string;
  const profile = await profileStore.get(uid);
  if (!profile) {
    return redirect('/onboarding');
  }
  return <ChatWindow />;
}