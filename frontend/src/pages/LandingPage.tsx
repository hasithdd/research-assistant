import { useNavigate } from 'react-router-dom';
import { UploadDropzone } from '../components/UploadDropzone';
import { useAppStore } from '../store/appStore';

export default function LandingPage() {
  const navigate = useNavigate();
  const { uploadPdf, isLoadingUpload, error, reset } = useAppStore((state) => ({
    uploadPdf: state.uploadPdf,
    isLoadingUpload: state.isLoadingUpload,
    error: state.error,
    reset: state.reset
  }));

  const handleFile = async (file: File) => {
    try {
      reset();
      const paperId = await uploadPdf(file);
      navigate(`/paper/${paperId}`);
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="min-h-screen bg-surface">
      <div className="mx-auto max-w-6xl px-4 py-16 flex flex-col items-center gap-10">
        <div className="text-center space-y-3">
          <p className="text-sm uppercase tracking-wide text-muted">M12 • Research Assistant</p>
          <h1 className="text-4xl font-bold text-ink">Chat with your research papers</h1>
          <p className="text-lg text-muted max-w-2xl">
            Upload a PDF, get an instant structured summary, and ask targeted questions with cited sources.
          </p>
        </div>
        <UploadDropzone onFile={handleFile} loading={isLoadingUpload} error={error} />
      </div>
    </div>
  );
}
