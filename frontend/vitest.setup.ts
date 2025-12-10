import '@testing-library/jest-dom';
import { vi } from 'vitest';

// jsdom lacks this; mock to avoid crashes when creating preview URLs in tests.
if (!('createObjectURL' in URL)) {
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	(URL as any).createObjectURL = vi.fn(() => 'blob:mock');
}
