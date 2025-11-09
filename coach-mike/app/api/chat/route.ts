import { NextRequest, NextResponse } from 'next/server';

/**
 * Proxies chat requests to the backend RAG API.
 *
 * Accepts a POST payload containing the user query and their profile. The
 * server-side handler adds any necessary authentication headers (e.g. a
 * secret API token) before forwarding the request to the configured API
 * endpoint. Responses are returned as-is to the client. This indirection
 * prevents exposing sensitive tokens in browser code and centralizes error
 * handling.
 */
export async function POST(req: NextRequest) {
  try {
    const { query, profile } = (await req.json()) as { query: string; profile: any };
    // Use API_URL (server-side) or fallback to NEXT_PUBLIC_RAG_API_URL
    const apiUrl = process.env.API_URL || process.env.NEXT_PUBLIC_RAG_API_URL || 'http://localhost:8000';
    if (!apiUrl) {
      return NextResponse.json({ error: 'API_URL or NEXT_PUBLIC_RAG_API_URL environment variable is not defined' }, { status: 500 });
    }
    const token = process.env.RAG_API_TOKEN;
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    const res = await fetch(`${apiUrl.replace(/\/$/, '')}/chat`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ query, profile }),
    });
    const text = await res.text();
    // If backend returns non-JSON (e.g. string), pass it through
    if (!res.ok) {
      return new NextResponse(text, { status: res.status });
    }
    return new NextResponse(text, {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (err: any) {
    return NextResponse.json({ error: err.message || 'Unknown error' }, { status: 500 });
  }
}