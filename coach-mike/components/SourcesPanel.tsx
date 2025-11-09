"use client";

interface SourcesPanelProps {
  sources: Array<Record<string, any>>;
  onClose: () => void;
}

/**
 * Displays the list of sources returned by the RAG backend. Each source is
 * rendered as a clickable item if it contains a URL. Otherwise the entire
 * object is stringified. The panel can be closed by the user.
 */
export default function SourcesPanel({ sources, onClose }: SourcesPanelProps) {
  if (!sources || sources.length === 0) return null;
  return (
    <div className="fixed right-0 top-0 h-full w-80 bg-white shadow-lg border-l p-4 overflow-y-auto z-50">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold">Sources</h2>
        <button
          aria-label="Fermer les sources"
          className="text-gray-500 hover:text-gray-700"
          onClick={onClose}
        >
          ×
        </button>
      </div>
      <ul className="space-y-3">
        {sources.map((source, idx) => (
          <li key={idx} className="p-2 border rounded-md bg-gray-50 hover:bg-gray-100">
            {source.url ? (
              <a href={source.url as string} target="_blank" rel="noopener" className="text-blue-600 underline">
                {source.url}
              </a>
            ) : (
              <pre className="text-xs whitespace-pre-wrap">{JSON.stringify(source, null, 2)}</pre>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}