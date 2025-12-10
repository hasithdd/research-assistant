import client from './client';
import type { Summary } from '../types';

export async function getSummary(paperId: string): Promise<Summary> {
  const { data } = await client.get<Summary>(`/summary/${paperId}`);
  return data;
}
