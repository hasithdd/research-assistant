import client from './client';
import type { Source } from '../types';

export interface ChatRequest {
  paper_id: string;
  query: string;
}

export interface ChatResponse {
  answer: string;
  sources?: Source[];
}

export async function askQuestion(paperId: string, query: string): Promise<ChatResponse> {
  const { data } = await client.post<ChatResponse>('/chat', { paper_id: paperId, query });
  return data;
}
