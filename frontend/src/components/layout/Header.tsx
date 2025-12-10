import { Link } from 'react-router-dom';
import { Brain } from 'lucide-react';

export function Header() {
  return (
    <header className="w-full border-b border-gray-200 bg-white sticky top-0 z-10">
      <div className="mx-auto max-w-6xl px-4 py-3 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2 text-ink font-semibold">
          <Brain className="h-5 w-5 text-accent" /> Research Assistant
        </Link>
        <div className="text-xs text-muted">Chat with your PDFs</div>
      </div>
    </header>
  );
}
