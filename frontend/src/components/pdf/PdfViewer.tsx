import { useState } from 'react';
import { Document, Page } from 'react-pdf';
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut } from 'lucide-react';
import clsx from 'clsx';

interface Props {
  file?: string | null;
}

export function PdfViewer({ file }: Props) {
  const [pageNumber, setPageNumber] = useState(1);
  const [numPages, setNumPages] = useState<number>(0);
  const [scale, setScale] = useState(1.1);

  const handleLoad = ({ numPages: total }: { numPages: number }) => {
    setNumPages(total);
    setPageNumber(1);
  };

  return (
    <div className="h-full w-full bg-gray-50 rounded-xl border border-gray-200 flex flex-col">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-white">
        <div className="flex items-center gap-2 text-sm text-muted">
          <button
            className="p-2 rounded-full hover:bg-gray-100 disabled:opacity-40"
            onClick={() => setScale((s) => Math.min(s + 0.1, 2))}
            aria-label="Zoom in"
          >
            <ZoomIn className="h-4 w-4" />
          </button>
          <button
            className="p-2 rounded-full hover:bg-gray-100 disabled:opacity-40"
            onClick={() => setScale((s) => Math.max(s - 0.1, 0.6))}
            aria-label="Zoom out"
          >
            <ZoomOut className="h-4 w-4" />
          </button>
        </div>
        <div className="flex items-center gap-2 text-sm text-muted">
          <button
            className="p-2 rounded-full hover:bg-gray-100 disabled:opacity-40"
            onClick={() => setPageNumber((p) => Math.max(p - 1, 1))}
            disabled={pageNumber <= 1}
            aria-label="Previous page"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <span className="text-xs text-ink">
            Page {pageNumber} {numPages ? `of ${numPages}` : ''}
          </span>
          <button
            className="p-2 rounded-full hover:bg-gray-100 disabled:opacity-40"
            onClick={() => setPageNumber((p) => (numPages ? Math.min(p + 1, numPages) : p + 1))}
            disabled={numPages ? pageNumber >= numPages : false}
            aria-label="Next page"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-auto flex items-center justify-center">
        {file ? (
          <Document file={file} onLoadSuccess={handleLoad} loading={<div className="text-sm text-muted">Loading PDF…</div>}>
            <Page pageNumber={pageNumber} scale={scale} className={clsx('shadow-sm transition-transform')} renderTextLayer={false} renderAnnotationLayer={false} />
          </Document>
        ) : (
          <div className="text-muted text-sm">No PDF loaded yet.</div>
        )}
      </div>
    </div>
  );
}
