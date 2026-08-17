import { stat, unlink, writeFile } from 'node:fs/promises';
import { resolve, sep, normalize, join } from 'node:path';

const KNOWN_EXTS = ['.png', '.jpg', '.jpeg', '.webp'] as const;

export class UnsafeKeyError extends Error {
  constructor(key: string) {
    super(`Unsafe headphone key: ${key}`);
    this.name = 'UnsafeKeyError';
  }
}

export function safeKey(key: string): string {
  if (!key) throw new UnsafeKeyError(key);
  if (key.includes('\0')) throw new UnsafeKeyError(key);
  if (key.includes('/') || key.includes('\\')) throw new UnsafeKeyError(key);
  if (key === '.' || key === '..' || key.includes('..')) throw new UnsafeKeyError(key);
  if (key !== normalize(key)) throw new UnsafeKeyError(key);
  return key;
}

export function picturePathFor(picturesDir: string, key: string, ext: string): string {
  const safe = safeKey(key);
  const root = resolve(picturesDir);
  const candidate = resolve(join(root, `${safe}${ext}`));
  if (!candidate.startsWith(root + sep) && candidate !== root) {
    throw new UnsafeKeyError(key);
  }
  return candidate;
}

export async function findExistingPicture(
  picturesDir: string,
  key: string,
): Promise<{ path: string; ext: string } | null> {
  for (const ext of KNOWN_EXTS) {
    const path = picturePathFor(picturesDir, key, ext);
    try {
      const s = await stat(path);
      if (s.isFile()) return { path, ext };
    } catch {
      /* try next */
    }
  }
  return null;
}

export async function savePicture(
  picturesDir: string,
  key: string,
  pngBytes: Buffer,
): Promise<{ writtenPath: string; removed: string[] }> {
  const target = picturePathFor(picturesDir, key, '.png');
  await writeFile(target, pngBytes);

  const removed: string[] = [];
  for (const ext of KNOWN_EXTS) {
    if (ext === '.png') continue;
    const path = picturePathFor(picturesDir, key, ext);
    try {
      await unlink(path);
      removed.push(path);
    } catch {
      /* not present */
    }
  }
  return { writtenPath: target, removed };
}

export function contentTypeFor(ext: string): string {
  switch (ext.toLowerCase()) {
    case '.png':
      return 'image/png';
    case '.jpg':
    case '.jpeg':
      return 'image/jpeg';
    case '.webp':
      return 'image/webp';
    default:
      return 'application/octet-stream';
  }
}
