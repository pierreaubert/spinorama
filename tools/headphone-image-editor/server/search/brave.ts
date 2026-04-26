import { type ImageHit, type SearchEngine, SearchEngineError } from './types.ts';

interface BraveImageResult {
  title?: string;
  url?: string;
  source?: string;
  thumbnail?: { src?: string };
  properties?: { url?: string };
  image?: { url?: string; width?: number; height?: number };
}

interface BraveImageResponse {
  results?: BraveImageResult[];
  message?: string;
}

const ENDPOINT = 'https://api.search.brave.com/res/v1/images/search';

export class BraveSearchEngine implements SearchEngine {
  readonly name = 'brave';

  constructor(private readonly apiKey: string) {
    if (!apiKey) {
      throw new Error('BRAVE_API_KEY is required for the brave search engine');
    }
  }

  async search(query: string, count: number): Promise<ImageHit[]> {
    const params = new URLSearchParams({
      q: query,
      count: String(Math.min(Math.max(count, 1), 50)),
      safesearch: 'strict',
      country: 'us',
    });
    const url = `${ENDPOINT}?${params.toString()}`;
    const res = await fetch(url, {
      headers: {
        'X-Subscription-Token': this.apiKey,
        Accept: 'application/json',
        'Accept-Encoding': 'gzip',
      },
    });

    if (!res.ok) {
      const body = await res.text().catch(() => '');
      throw new SearchEngineError(
        `Brave Search returned ${res.status}: ${body.slice(0, 200)}`,
        res.status === 401 || res.status === 403 ? 502 : 502,
      );
    }

    const data = (await res.json()) as BraveImageResponse;
    const results = data.results ?? [];
    return results
      .map(toHit)
      .filter((hit): hit is ImageHit => hit !== null)
      .slice(0, count);
  }
}

function toHit(r: BraveImageResult): ImageHit | null {
  const imageUrl = r.properties?.url ?? r.image?.url;
  const thumbnailUrl = r.thumbnail?.src ?? imageUrl;
  const sourceUrl = r.url ?? r.source ?? '';
  if (!imageUrl || !thumbnailUrl) return null;
  return {
    title: r.title ?? '',
    thumbnailUrl,
    imageUrl,
    sourceUrl,
    width: r.image?.width,
    height: r.image?.height,
  };
}
