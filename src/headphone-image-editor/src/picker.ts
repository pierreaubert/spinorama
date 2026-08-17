import { search, type ImageHit } from './api.ts';

export interface PickerOptions {
  query: string;
  onPick: (hit: ImageHit) => void;
  onClose: () => void;
}

export async function openPicker(opts: PickerOptions): Promise<void> {
  const root = document.createElement('div');
  root.className = 'modal';
  root.innerHTML = `
    <div class="picker">
      <header>
        <strong>Pick a replacement image</strong>
        <span class="muted">${escapeHtml(opts.query)}</span>
        <button data-role="close" type="button">Close</button>
      </header>
      <div class="picker-grid" data-role="grid">
        <p class="status">Searching…</p>
      </div>
    </div>
  `;
  document.body.append(root);

  root.querySelector<HTMLButtonElement>('[data-role=close]')!.addEventListener('click', () => {
    root.remove();
    opts.onClose();
  });

  const grid = root.querySelector<HTMLElement>('[data-role=grid]')!;

  try {
    const { hits, engine } = await search(opts.query, 10);
    if (hits.length === 0) {
      grid.innerHTML = '<p class="status">No images found.</p>';
      return;
    }
    grid.innerHTML = '';
    grid.dataset.engine = engine;
    for (const hit of hits) {
      grid.append(renderHit(hit, () => opts.onPick(hit)));
    }
  } catch (err) {
    grid.innerHTML = `<p class="status error">${escapeHtml((err as Error).message)}</p>`;
  }
}

function renderHit(hit: ImageHit, onPick: () => void): HTMLElement {
  const card = document.createElement('button');
  card.type = 'button';
  card.className = 'hit';
  const dims =
    hit.width && hit.height ? `<span class="muted">${hit.width}×${hit.height}</span>` : '';
  card.innerHTML = `
    <img loading="lazy" alt="" src="${escapeAttr(hit.thumbnailUrl)}">
    <div class="hit-meta">
      <span class="hit-title">${escapeHtml(hit.title || hit.sourceUrl)}</span>
      ${dims}
    </div>
  `;
  card.addEventListener('click', onPick);
  return card;
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function escapeAttr(s: string): string {
  return escapeHtml(s);
}
