export interface ImageHit {
  title: string;
  thumbnailUrl: string;
  imageUrl: string;
  sourceUrl: string;
  width?: number;
  height?: number;
}

export interface SearchEngine {
  readonly name: string;
  search(query: string, count: number): Promise<ImageHit[]>;
}

export class SearchEngineError extends Error {
  constructor(
    message: string,
    public readonly status = 502,
  ) {
    super(message);
    this.name = 'SearchEngineError';
  }
}
