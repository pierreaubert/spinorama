export interface HeadphoneEntry {
  key: string;
  brand: string;
  model: string;
  shape: string;
  price?: string;
  picture: string | null;
}

export interface ImageHit {
  title: string;
  thumbnailUrl: string;
  imageUrl: string;
  sourceUrl: string;
  width?: number;
  height?: number;
}

export interface SearchResponse {
  engine: string;
  hits: ImageHit[];
}

export interface SaveResponse {
  written: string;
  removed: string[];
  bytes: number;
}

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return (await res.json()) as T;
}

async function postJson<T>(url: string, body: unknown): Promise<T> {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  return (await res.json()) as T;
}

export function listHeadphones(): Promise<HeadphoneEntry[]> {
  return getJson<HeadphoneEntry[]>('/api/headphones');
}

export function pictureUrl(key: string): string {
  return `/api/picture/${encodeURIComponent(key)}`;
}

export function search(query: string, count = 10): Promise<SearchResponse> {
  const params = new URLSearchParams({ q: query, count: String(count) });
  return getJson<SearchResponse>(`/api/search?${params.toString()}`);
}

export function proxiedImageUrl(imageUrl: string): string {
  return `/api/proxy?url=${encodeURIComponent(imageUrl)}`;
}

export function savePicture(key: string, pngBase64: string): Promise<SaveResponse> {
  return postJson<SaveResponse>('/api/save', { key, pngBase64, confirm: true });
}
