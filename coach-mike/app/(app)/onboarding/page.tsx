import { getServerSession } from 'next-auth';
import { redirect } from 'next/navigation';
import { authOptions } from '../../../lib/auth';
import { profileStore } from '../../../lib/store';
import OnboardingForm from '../../../components/ProfileForm';

export default async function OnboardingPage() {
  const session = await getServerSession(authOptions);
  if (!session || !(session.user as any)?.id) {
    return redirect('/login');
  }
  const uid = (session.user as any).id as string;
  const existing = await profileStore.get(uid);
  if (existing) {
    // User already completed onboarding; go straight to chat
    return redirect('/chat');
  }
  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-4">Onboarding</h1>
      <p className="mb-4">Merci de remplir ces informations afin de personnaliser vos séances d'entraînement.</p>
      {/* OnboardingForm is a client component imported from components */}
      <OnboardingForm />
    </div>
  );
}