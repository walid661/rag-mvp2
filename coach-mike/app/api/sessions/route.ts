import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '../../../lib/auth';
import { chatStore } from '../../../lib/store';

/**
 * API route for managing chat sessions. Supports listing existing sessions and
 * creating a new session. Authentication is required; each user only has
 * access to their own sessions.
 */
export async function GET() {
  const session = await getServerSession(authOptions);
  if (!session || !(session.user as any)?.id) {
    return new NextResponse('Unauthorized', { status: 401 });
  }
  const uid = (session.user as any).id as string;
  const sessions = await chatStore.listSessions(uid);
  return NextResponse.json({ sessions });
}

export async function POST(req: NextRequest) {
  const session = await getServerSession(authOptions);
  if (!session || !(session.user as any)?.id) {
    return new NextResponse('Unauthorized', { status: 401 });
  }
  const uid = (session.user as any).id as string;
  const { title } = (await req.json()) as { title?: string };
  const id = await chatStore.createSession(uid, title);
  return NextResponse.json({ id });
}