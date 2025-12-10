import client from './client';
import type { Summary } from '../types';

export interface UploadResponse {
  paper_id: string;
  summary: Summary;
}

export async function uploadPdf(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const { data } = await client.post<UploadResponse>('/upload/pdf', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000, // 120 seconds for PDF processing (embedding + summarization)
    onUploadProgress: (progressEvent) => {
      if (progressEvent.total) {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        console.log(`Upload progress: ${percentCompleted}%`);
      }
    }
  });

  return data;
}
