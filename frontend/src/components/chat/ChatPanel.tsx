import { FormEvent, useEffect, useRef, useState } from 'react';
import { Loader2, Sparkles } from 'lucide-react';
import type { Message } from '../../types';

type Props = {
  messages: Message[];
  onSend: (text: string) => Promise<void> | void;
  loading?: boolean;
};

export function ChatPanel({ messages, onSend, loading }: Props) {
  const [text, setText] = useState('');
  const listRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const node = listRef.current;
    if (node && typeof node.scrollTo === 'function') {
      node.scrollTo({ top: node.scrollHeight, behavior: 'smooth' });
    }
  }, [messages.length]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;
    const payload = text;
    setText('');
    await onSend(payload);
  };

  return (
    <div className="flex h-full flex-col bg-white border border-gray-200 rounded-xl shadow-sm">
      <div className="px-4 py-3 border-b border-gray-200 flex items-center gap-2">
        <Sparkles className="h-4 w-4 text-accent" />
        <h3 className="text-sm font-semibold text-ink">Chat about this paper</h3>
      </div>
      <div ref={listRef} className="flex-1 overflow-auto px-4 py-3 space-y-3" data-testid="chat-history">
        {messages.length === 0 && (
          <p className="text-sm text-muted">Ask anything about the PDF. Sources will appear with the answer.</p>
        )}
        {messages.map((message) => (
          <div key={message.id} className="flex flex-col gap-1">
            <div className="text-xs font-semibold text-muted uppercase">{message.role === 'user' ? 'You' : 'Assistant'}</div>
            <div className="rounded-xl bg-gray-50 px-4 py-3 text-sm text-ink shadow-sm">
              {message.text}
              {message.sources && message.sources.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {message.sources.map((source, idx) => (
                    <span
                      key={`${message.id}-source-${idx}`}
                      className="text-[11px] rounded-full bg-blue-50 text-accent px-3 py-1"
                    >
                      {source.section ? `${source.section}${source.index !== undefined ? ` #${source.index}` : ''}` : 'Source'}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
      <form onSubmit={handleSubmit} className="border-t border-gray-200 p-3 bg-white">
        <div className="relative">
          <input
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Ask a question about the paper..."
            className="w-full rounded-full border border-gray-200 px-4 py-3 pr-24 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading}
            className="absolute right-2 top-1/2 -translate-y-1/2 rounded-full bg-accent px-4 py-2 text-white text-sm shadow-sm disabled:opacity-50"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Send'}
          </button>
        </div>
      </form>
    </div>
  );
}
