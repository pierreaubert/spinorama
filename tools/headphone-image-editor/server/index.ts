import { createReadStream } from 'node:fs';
import { readFile } from 'node:fs/promises';
import { createServer, type IncomingMessage, type ServerResponse } from 'node:http';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

import { loadHeadphones } from './headphones.ts';
import {
  contentTypeFor,
  findExistingPicture,
  safeKey,
  savePicture,
  UnsafeKeyError,
} from './pictures.ts';
import { getEngine } from './search/registry.ts';
import { SearchEngineError } from './search/types.ts';

const __dirname = dirname(fileURLToPath(import.meta.url));
const APP_ROOT = resolve(__dirname, '..');
const REPO_ROOT = resolve(APP_ROOT, '..', '..');

const PORT = Number(process.env.PORT ?? 5174);
const PICTURES_DIR = resolve(
  APP_ROOT,
  process.env.PICTURES_DIR ?? '../../datas/pictures',
);
const HEADPHONES_JSON = resolve(
  APP_ROOT,
  process.env.HEADPHONES_JSON ?? './data/headphones.json',
);

await loadEnvFile();

type Handler = (
  req: IncomingMessage,
  res: ServerResponse,
  url: URL,
) => Promise<void> | void;

const server = createServer(async (req, res) => {
  try {
    const url = new URL(req.url ?? '/', `http://${req.headers.host ?? 'localhost'}`);
    const handler = route(req.method ?? 'GET', url.pathname);
    if (!handler) {
      send(res, 404, { error: 'Not found' });
      return;
    }
    await handler(req, res, url);
  } catch (err) {
    handleError(res, err);
  }
});

function route(method: string, pathname: string): Handler | null {
  if (method === 'GET' && pathname === '/api/headphones') return handleList;
  if (method === 'GET' && pathname.startsWith('/api/picture/')) return handlePicture;
  if (method === 'GET' && pathname === '/api/search') return handleSearch;
  if (method === 'GET' && pathname === '/api/proxy') return handleProxy;
  if (method === 'POST' && pathname === '/api/save') return handleSave;
  if (method === 'GET' && pathname === '/api/health') return (_req, res) => send(res, 200, { ok: true });
  return null;
}

const handleList: Handler = async (_req, res) => {
  const entries = await loadHeadphones(HEADPHONES_JSON);
  send(res, 200, entries);
};

const handlePicture: Handler = async (_req, res, url) => {
  const key = decodeURIComponent(url.pathname.slice('/api/picture/'.length));
  safeKey(key);
  const found = await findExistingPicture(PICTURES_DIR, key);
  if (!found) {
    send(res, 404, { error: 'No picture for this key' });
    return;
  }
  res.writeHead(200, {
    'Content-Type': contentTypeFor(found.ext),
    'Cache-Control': 'no-store',
  });
  createReadStream(found.path).pipe(res);
};

const handleSearch: Handler = async (_req, res, url) => {
  const q = url.searchParams.get('q')?.trim();
  const count = Number(url.searchParams.get('count') ?? '10');
  if (!q) {
    send(res, 400, { error: 'Missing q' });
    return;
  }
  const engine = getEngine();
  const hits = await engine.search(q, Number.isFinite(count) ? count : 10);
  send(res, 200, { engine: engine.name, hits });
};

const handleProxy: Handler = async (_req, res, url) => {
  const target = url.searchParams.get('url');
  if (!target) {
    send(res, 400, { error: 'Missing url' });
    return;
  }
  let parsed: URL;
  try {
    parsed = new URL(target);
  } catch {
    send(res, 400, { error: 'Invalid url' });
    return;
  }
  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
    send(res, 400, { error: 'Only http(s) urls allowed' });
    return;
  }
  const upstream = await fetch(parsed, {
    headers: { 'User-Agent': 'spinorama-headphone-image-editor/0.1' },
    redirect: 'follow',
  });
  if (!upstream.ok || !upstream.body) {
    send(res, 502, { error: `Upstream returned ${upstream.status}` });
    return;
  }
  const ctype = upstream.headers.get('content-type') ?? 'application/octet-stream';
  if (!ctype.startsWith('image/')) {
    send(res, 415, { error: `Refusing non-image content-type ${ctype}` });
    return;
  }
  res.writeHead(200, {
    'Content-Type': ctype,
    'Cache-Control': 'no-store',
  });
  const { Readable } = await import('node:stream');
  Readable.fromWeb(upstream.body).pipe(res);
};

interface SaveBody {
  key?: unknown;
  pngBase64?: unknown;
  confirm?: unknown;
}

const handleSave: Handler = async (req, res) => {
  const body = await readJson<SaveBody>(req);
  if (body.confirm !== true) {
    send(res, 400, { error: 'Missing confirm: true' });
    return;
  }
  if (typeof body.key !== 'string' || typeof body.pngBase64 !== 'string') {
    send(res, 400, { error: 'key and pngBase64 (string) are required' });
    return;
  }
  const key = safeKey(body.key);
  const cleaned = body.pngBase64.replace(/^data:image\/png;base64,/, '');
  const bytes = Buffer.from(cleaned, 'base64');
  if (bytes.length === 0) {
    send(res, 400, { error: 'Empty image payload' });
    return;
  }
  // Sanity check PNG magic.
  const magic = bytes.subarray(0, 8);
  const expected = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
  if (!magic.equals(expected)) {
    send(res, 400, { error: 'Not a PNG (bad magic)' });
    return;
  }
  const result = await savePicture(PICTURES_DIR, key, bytes);
  send(res, 200, {
    written: result.writtenPath,
    removed: result.removed,
    bytes: bytes.length,
  });
};

function send(res: ServerResponse, status: number, body: unknown): void {
  const payload = Buffer.from(JSON.stringify(body));
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': payload.length,
  });
  res.end(payload);
}

async function readJson<T>(req: IncomingMessage): Promise<T> {
  const chunks: Buffer[] = [];
  let total = 0;
  const max = 32 * 1024 * 1024; // 32 MB cap
  for await (const chunk of req) {
    const buf = chunk as Buffer;
    total += buf.length;
    if (total > max) throw new HttpError(413, 'Payload too large');
    chunks.push(buf);
  }
  const text = Buffer.concat(chunks).toString('utf-8');
  if (!text) return {} as T;
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new HttpError(400, 'Invalid JSON');
  }
}

class HttpError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

function handleError(res: ServerResponse, err: unknown): void {
  if (err instanceof UnsafeKeyError) {
    send(res, 400, { error: err.message });
    return;
  }
  if (err instanceof HttpError) {
    send(res, err.status, { error: err.message });
    return;
  }
  if (err instanceof SearchEngineError) {
    send(res, err.status, { error: err.message });
    return;
  }
  const message = err instanceof Error ? err.message : String(err);
  console.error('[server] unhandled', err);
  send(res, 500, { error: message });
}

async function loadEnvFile(): Promise<void> {
  const envPath = resolve(APP_ROOT, '.env');
  try {
    const text = await readFile(envPath, 'utf-8');
    for (const rawLine of text.split('\n')) {
      const line = rawLine.trim();
      if (!line || line.startsWith('#')) continue;
      const eq = line.indexOf('=');
      if (eq < 0) continue;
      const key = line.slice(0, eq).trim();
      let value = line.slice(eq + 1).trim();
      if (
        (value.startsWith('"') && value.endsWith('"')) ||
        (value.startsWith("'") && value.endsWith("'"))
      ) {
        value = value.slice(1, -1);
      }
      if (!(key in process.env)) {
        process.env[key] = value;
      }
    }
  } catch (err) {
    const e = err as NodeJS.ErrnoException;
    if (e.code !== 'ENOENT') throw err;
  }
}

server.listen(PORT, '127.0.0.1', () => {
  console.log(`[server] http://127.0.0.1:${PORT}`);
  console.log(`[server] pictures dir: ${PICTURES_DIR}`);
  console.log(`[server] headphones json: ${HEADPHONES_JSON}`);
  console.log(`[server] repo root: ${REPO_ROOT}`);
});
