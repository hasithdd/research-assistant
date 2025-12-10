import { MemoryRouter } from 'react-router-dom';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../App';
import { useAppStore } from '../store/appStore';

const mockUpload = vi.fn(async () => ({ paper_id: 'paper-1', summary: { title: 'Mock Paper' } }));
const mockSummary = vi.fn(async () => ({ title: 'Mock Paper', abstract: 'A summary' }));
const mockChat = vi.fn(async () => ({ answer: 'Mock answer', sources: [{ section: 'intro', index: 1 }] }));

vi.mock('../api/upload', () => ({ uploadPdf: (file: File) => mockUpload(file) }));
vi.mock('../api/summary', () => ({ getSummary: (paperId: string) => mockSummary(paperId) }));
vi.mock('../api/chat', () => ({ askQuestion: (paperId: string, query: string) => mockChat(paperId, query) }));
vi.mock('react-pdf', () => {
  const React = require('react');
  return {
    Document: ({ children }: { children: React.ReactNode }) => <div data-testid="mock-document">{children}</div>,
    Page: ({ pageNumber }: { pageNumber: number }) => <div data-testid={`mock-page-${pageNumber}`} data-page={pageNumber} />,
    pdfjs: { GlobalWorkerOptions: { workerSrc: '' } }
  };
});

function resetStore() {
  useAppStore.getState().reset();
}

describe('Research Assistant UI', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetStore();
  });

  it('uploads a PDF then loads summary and chat', async () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>
    );

    const fileInput = screen.getByTestId('file-input') as HTMLInputElement;
    const file = new File(['dummy'], 'paper.pdf', { type: 'application/pdf' });
    await userEvent.upload(fileInput, file);

    await waitFor(() => expect(mockUpload).toHaveBeenCalled());

    await waitFor(() => expect(screen.getByText(/Interactive View/i)).toBeInTheDocument());
    expect(screen.getByText('Mock Paper')).toBeInTheDocument();

    const questionInput = screen.getByPlaceholderText(/Ask a question/i);
    await userEvent.type(questionInput, 'What is this about?');
    await userEvent.click(screen.getByText('Send'));

    await waitFor(() => expect(mockChat).toHaveBeenCalledWith('paper-1', 'What is this about?'));
    await waitFor(() => expect(screen.getByText('Mock answer')).toBeInTheDocument());
  });
});
