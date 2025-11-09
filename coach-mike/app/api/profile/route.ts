import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '../../../lib/auth';
import { profileStore } from '../../../lib/store';

/**
 * API route for reading and writing the current user's profile. The client
 * uses these endpoints to retrieve existing onboarding data or submit new
 * information. All requests require authentication.
 */
export async function GET() {
  const session = await getServerSession(authOptions);
  if (!session || !(session.user as any)?.id) {
    return new NextResponse('Unauthorized', { status: 401 });
  }
  const uid = (session.user as any).id as string;
  const profile = await profileStore.get(uid);
  return NextResponse.json({ profile });
}

export async function POST(req: NextRequest) {
  const session = await getServerSession(authOptions);
  if (!session || !(session.user as any)?.id) {
    return new NextResponse('Unauthorized', { status: 401 });
  }
  const uid = (session.user as any).id as string;
  const { profile } = (await req.json()) as { profile: any };
  await profileStore.upsert(uid, profile);
  return NextResponse.json({ success: true });
}