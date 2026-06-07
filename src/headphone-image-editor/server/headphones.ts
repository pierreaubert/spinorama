import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';

export interface HeadphoneEntry {
  key: string;
  brand: string;
  model: string;
  shape: string;
  price?: string;
  picture: string | null;
}

export async function loadHeadphones(jsonPath: string): Promise<HeadphoneEntry[]> {
  const abs = resolve(jsonPath);
  let text: string;
  try {
    text = await readFile(abs, 'utf-8');
  } catch (err) {
    const e = err as NodeJS.ErrnoException;
    if (e.code === 'ENOENT') {
      throw new Error(
        `Headphone data not found at ${abs}. Run \`npm run sync\` (or python3 scripts/dump_headphones.py) first.`,
      );
    }
    throw err;
  }
  const parsed = JSON.parse(text) as HeadphoneEntry[];
  if (!Array.isArray(parsed)) {
    throw new Error(`${abs} is not a JSON array`);
  }
  return parsed;
}
