"use client";

interface MessageItemProps {
  role: 'user' | 'assistant';
  content: string;
}

/**
 * Renders a single chat message bubble. User messages are right-aligned and
 * assistant messages are left-aligned. Uses simple styling for clarity.
 */
export default function MessageItem({ role, content }: MessageItemProps) {
  const isUser = role === 'user';
  const containerClass = `flex mb-2 ${isUser ? 'justify-end' : 'justify-start'}`;
  const bubbleClass = isUser
    ? 'px-4 py-2 rounded-lg max-w-xs shadow bg-indigo-600 text-white rounded-br-none'
    : 'px-4 py-2 rounded-lg max-w-xs shadow bg-gray-200 text-gray-900 rounded-bl-none';
  return (
    <div className={containerClass}>
      <div className={bubbleClass}>
        <p className="whitespace-pre-wrap">{content}</p>
      </div>
    </div>
  );
}