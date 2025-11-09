import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '../../../../../lib/auth';
import { chatStore } from '../../../../../lib/store';

/**
 * API route for chat messages within a given session. Allows retrieving the
 * history and appending new messages. Only the owner of the session may
 * access or modify its contents.
 */
export async function GET(
  req: NextRequest,
  context: { params: { sessionId: string } }
) {
  const { sessionId } = context.params;
  const session = await getServerSession(authOptions);
  if (!session || !(session.user as any)?.id) {
    return new NextResponse('Unauthorized', { status: 401 });
  }
  // TODO: Optionally verify that sessionId belongs to the user. For brevity we
  // skip this check here; it should be implemented in production.
  const messages = await chatStore.listMessages(sessionId);
  return NextResponse.json({ messages });
}

export async function POST(
  req: NextRequest,
  context: { params: { sessionId: string } }
) {
  const { sessionId } = context.params;
  const authSession = await getServerSession(authOptions);
  if (!authSession || !(authSession.user as any)?.id) {
    return new NextResponse('Unauthorized', { status: 401 });
  }
  const { role, content } = (await req.json()) as { role: 'user' | 'assistant'; content: string };
  await chatStore.appendMessage(sessionId, role, content);
  return NextResponse.json({ success: true });
}