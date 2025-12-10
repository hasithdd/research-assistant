import { useCallback, useRef, useState } from 'react';
import { UploadCloud, FilePlus2, Loader2 } from 'lucide-react';
import clsx from 'clsx';

type Props = {
  onFile: (file: File) => void;
  loading?: boolean;
  error?: string | null;
};

export function UploadDropzone({ onFile, loading, error }: Props) {
  const [isDragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const handleFile = useCallback(
    (files?: FileList | null) => {
      const file = files?.[0];
      if (file) onFile(file);
    },
    [onFile]
  );

  return (
    <div className="w-full max-w-xl">
      <div
        className={clsx(
          'border-2 border-dashed rounded-2xl p-10 text-center transition-all bg-white shadow-sm',
          isDragging ? 'border-accent bg-blue-50' : 'border-gray-200',
          loading && 'opacity-70'
        )}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          handleFile(e.dataTransfer.files);
        }}
        role="button"
        aria-label="Upload PDF"
      >
        <div className="flex flex-col items-center gap-4">
          <div className="h-14 w-14 rounded-full bg-blue-50 flex items-center justify-center">
            {loading ? <Loader2 className="h-8 w-8 animate-spin text-accent" /> : <UploadCloud className="h-8 w-8 text-accent" />}
          </div>
          <div>
            <p className="text-lg font-semibold text-ink">Drop your PDF here</p>
            <p className="text-sm text-muted">We will parse and summarize it for you.</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              className="inline-flex items-center gap-2 rounded-full bg-accent px-4 py-2 text-white shadow-sm hover:shadow-md transition"
              disabled={loading}
            >
              <FilePlus2 className="h-4 w-4" />
              Choose PDF
            </button>
            <span className="text-sm text-muted">or drag & drop</span>
          </div>
          {error && <p className="text-sm text-red-500">{error}</p>}
        </div>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={(e) => handleFile(e.target.files)}
          disabled={loading}
          data-testid="file-input"
        />
      </div>
    </div>
  );
}
