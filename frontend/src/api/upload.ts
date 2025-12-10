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
    headers: { 'Content-Type': 'multipart/form-data' }
  });

  return data;
}
