import { BraveSearchEngine } from './brave.ts';
import type { SearchEngine } from './types.ts';

let cached: SearchEngine | null = null;

export function getEngine(): SearchEngine {
  if (cached) return cached;
  const name = (process.env.SEARCH_ENGINE ?? 'brave').toLowerCase();
  switch (name) {
    case 'brave':
      cached = new BraveSearchEngine(process.env.BRAVE_API_KEY ?? '');
      return cached;
    default:
      throw new Error(`Unknown SEARCH_ENGINE: ${name}`);
  }
}
