import { useState } from 'react';
import * as Collapsible from '@radix-ui/react-collapsible';
import { ChevronDown, ChevronUp, NotebookPen } from 'lucide-react';
import type { Summary } from '../../types';

type Props = {
  summary: Summary | null;
};

export function SummaryDrawer({ summary }: Props) {
  const [open, setOpen] = useState(true);
  const fields: Array<{ label: string; key: keyof Summary }> = [
    { label: 'Title', key: 'title' },
    { label: 'Authors', key: 'authors' },
    { label: 'Abstract', key: 'abstract' },
    { label: 'Methodology', key: 'methodology' },
    { label: 'Key Results', key: 'key_results' },
    { label: 'Conclusion', key: 'conclusion' }
  ];

  return (
    <Collapsible.Root open={open} onOpenChange={setOpen} className="border border-gray-200 rounded-xl bg-white shadow-sm">
      <Collapsible.Trigger className="w-full flex items-center justify-between px-4 py-3">
        <div className="flex items-center gap-2 text-sm font-semibold text-ink">
          <NotebookPen className="h-4 w-4 text-accent" /> Summary
        </div>
        {open ? <ChevronUp className="h-4 w-4 text-muted" /> : <ChevronDown className="h-4 w-4 text-muted" />}
      </Collapsible.Trigger>
      <Collapsible.Content className="px-4 pb-4 space-y-3 text-sm">
        {!summary && <p className="text-muted">No summary loaded yet.</p>}
        {summary &&
          fields.map(({ label, key }) => {
            const value = summary[key];
            if (!value) return null;
            return (
              <div key={key} className="border border-gray-100 rounded-lg p-3 bg-gray-50">
                <div className="text-xs uppercase text-muted font-semibold">{label}</div>
                <div className="text-ink mt-1 whitespace-pre-wrap">
                  {Array.isArray(value) ? value.join(', ') : String(value)}
                </div>
              </div>
            );
          })}
      </Collapsible.Content>
    </Collapsible.Root>
  );
}
