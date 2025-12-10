import { useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ChatPanel } from '../components/chat/ChatPanel';
import { PdfViewer } from '../components/pdf/PdfViewer';
import { useAppStore } from '../store/appStore';

export default function PaperPage() {
  const { paperId } = useParams<{ paperId: string }>();
  const navigate = useNavigate();

  const {
    currentPaperId,
    pdfUrl,
    summary,
    messages,
    fetchSummary,
    askQuestion,
    setPaperContext,
    isLoadingChat,
    isLoadingSummary,
    error
  } = useAppStore((state) => ({
    currentPaperId: state.currentPaperId,
    pdfUrl: state.pdfUrl,
    summary: state.summary,
    messages: state.messages,
    fetchSummary: state.fetchSummary,
    askQuestion: state.askQuestion,
    setPaperContext: state.setPaperContext,
    isLoadingChat: state.isLoadingChat,
    isLoadingSummary: state.isLoadingSummary,
    error: state.error
  }));

  useEffect(() => {
    if (!paperId) return;
    setPaperContext(paperId);
    if (!summary || paperId !== currentPaperId) {
      fetchSummary(paperId).catch((e) => console.error(e));
    }
  }, [paperId, fetchSummary, summary, currentPaperId, setPaperContext]);

  useEffect(() => {
    if (!paperId) navigate('/');
  }, [paperId, navigate]);

  const handleSend = async (text: string) => {
    if (!paperId) return;
    await askQuestion(paperId, text);
  };

  return (
    <div className="min-h-screen bg-surface">
      <div className="mx-auto max-w-6xl px-4 py-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs uppercase tracking-wide text-muted">Paper</p>
            <h2 className="text-2xl font-semibold text-ink">Interactive View</h2>
            {error && <p className="text-sm text-red-500">{error}</p>}
          </div>
          <button
            onClick={() => navigate('/')}
            className="text-sm text-accent font-medium border border-accent px-3 py-2 rounded-full hover:bg-blue-50"
          >
            Upload another
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 auto-rows-[minmax(0,1fr)]">
          <div className="min-h-[65vh] lg:min-h-[75vh]">
            <PdfViewer file={pdfUrl} />
          </div>

          <div className="flex flex-col min-h-[65vh] lg:min-h-[75vh]">
            <ChatPanel messages={messages} onSend={handleSend} loading={isLoadingChat} />
          </div>
        </div>
      </div>
    </div>
  );
}
