export interface Summary {
  title?: string;
  authors?: string[];
  abstract?: string;
  methodology?: string;
  key_results?: string;
  conclusion?: string;
  [key: string]: unknown;
}

export interface Source {
  section?: string;
  index?: number;
  raw?: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  sources?: Source[];
  pending?: boolean;
}
