import { create } from 'zustand';
import { askQuestion as askQuestionApi } from '../api/chat';
import { getSummary } from '../api/summary';
import { uploadPdf as uploadPdfApi } from '../api/upload';
import type { Message, Summary } from '../types';

type AppState = {
  currentPaperId: string | null;
  pdfUrl: string | null;
  summary: Summary | null;
  messages: Message[];
  isLoadingUpload: boolean;
  isLoadingSummary: boolean;
  isLoadingChat: boolean;
  error: string | null;
  uploadPdf: (file: File) => Promise<string>;
  fetchSummary: (paperId: string) => Promise<Summary>;
  askQuestion: (paperId: string, query: string) => Promise<void>;
  appendMessage: (message: Message) => void;
  setPaperContext: (paperId: string, pdfUrl?: string | null) => void;
  reset: () => void;
};

const randomId = () => crypto.randomUUID();

export const useAppStore = create<AppState>((set, get) => ({
  currentPaperId: null,
  pdfUrl: null,
  summary: null,
  messages: [],
  isLoadingUpload: false,
  isLoadingSummary: false,
  isLoadingChat: false,
  error: null,

  uploadPdf: async (file: File) => {
    set({ isLoadingUpload: true, error: null });
    try {
      const { paper_id, summary } = await uploadPdfApi(file);
      const url = URL.createObjectURL(file);
      set({
        currentPaperId: paper_id,
        pdfUrl: url,
        summary,
        messages: [],
        error: null
      });
      return paper_id;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Upload failed';
      set({ error: message });
      throw error;
    } finally {
      set({ isLoadingUpload: false });
    }
  },

  fetchSummary: async (paperId: string) => {
    set({ isLoadingSummary: true, error: null });
    try {
      const data = await getSummary(paperId);
      set({ summary: data });
      return data;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to load summary';
      set({ error: message });
      throw error;
    } finally {
      set({ isLoadingSummary: false });
    }
  },

  askQuestion: async (paperId: string, query: string) => {
    const userMessage: Message = { id: randomId(), role: 'user', text: query };
    const pendingId = randomId();

    set((state) => ({
      messages: [...state.messages, userMessage, { id: pendingId, role: 'assistant', text: 'Thinking…', pending: true }],
      isLoadingChat: true,
      error: null
    }));

    try {
      const { answer, sources } = await askQuestionApi(paperId, query);
      set((state) => ({
        messages: state.messages.map((msg) =>
          msg.id === pendingId ? { ...msg, text: answer, sources, pending: false } : msg
        )
      }));
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Chat failed';
      set((state) => ({
        messages: state.messages.map((msg) =>
          msg.id === pendingId ? { ...msg, text: message, pending: false } : msg
        ),
        error: message
      }));
      throw error;
    } finally {
      set({ isLoadingChat: false });
    }
  },

  appendMessage: (message: Message) => set((state) => ({ messages: [...state.messages, message] })),

  setPaperContext: (paperId: string, pdfUrl?: string | null) =>
    set((state) => ({
      currentPaperId: paperId,
      pdfUrl: pdfUrl ?? state.pdfUrl
    })),

  reset: () =>
    set({
      currentPaperId: null,
      pdfUrl: null,
      summary: null,
      messages: [],
      isLoadingUpload: false,
      isLoadingSummary: false,
      isLoadingChat: false,
      error: null
    })
}));
