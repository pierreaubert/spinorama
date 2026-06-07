import { listHeadphones, pictureUrl, type HeadphoneEntry } from './api.ts';
import { openEditor } from './editor.ts';
import { openPicker } from './picker.ts';

export async function mountGrid(root: HTMLElement): Promise<void> {
  root.innerHTML = `
    <div class="toolbar">
      <input data-role="search" type="search" placeholder="Filter brand or model…" autofocus>
      <span data-role="count" class="muted"></span>
    </div>
    <div data-role="grid" class="grid"></div>
  `;

  const searchInput = root.querySelector<HTMLInputElement>('[data-role=search]')!;
  const grid = root.querySelector<HTMLElement>('[data-role=grid]')!;
  const count = root.querySelector<HTMLElement>('[data-role=count]')!;

  let entries: HeadphoneEntry[] = [];
  try {
    entries = await listHeadphones();
  } catch (err) {
    grid.innerHTML = `<p class="status error">Failed to load headphones: ${escapeHtml(
      (err as Error).message,
    )}</p>`;
    return;
  }

  const render = (filter: string): void => {
    const f = filter.trim().toLowerCase();
    const filtered = f
      ? entries.filter((e) => `${e.brand} ${e.model}`.toLowerCase().includes(f))
      : entries;
    count.textContent = `${filtered.length} / ${entries.length}`;
    grid.replaceChildren(...filtered.map(renderCard));
  };

  searchInput.addEventListener('input', () => render(searchInput.value));
  render('');

  function renderCard(entry: HeadphoneEntry): HTMLElement {
    const card = document.createElement('article');
    card.className = 'card';
    card.dataset.key = entry.key;
    const imgSrc = entry.picture ? pictureUrl(entry.key) : '';
    const imgHtml = imgSrc
      ? `<img loading="lazy" alt="" src="${escapeAttr(imgSrc)}">`
      : '<div class="placeholder">no picture</div>';
    card.innerHTML = `
      <div class="card-img">${imgHtml}</div>
      <div class="card-meta">
        <strong>${escapeHtml(entry.brand)}</strong>
        <span>${escapeHtml(entry.model)}</span>
        <span class="muted">${escapeHtml(entry.shape)}${
          entry.price ? ` · $${escapeHtml(entry.price)}` : ''
        }</span>
      </div>
    `;
    card.addEventListener('click', () => onPick(entry, card));
    return card;
  }

  function onPick(entry: HeadphoneEntry, card: HTMLElement): void {
    openPicker({
      query: `${entry.brand} ${entry.model} headphone product photo`,
      onClose: () => {},
      onPick: (hit) => {
        document.querySelectorAll('.modal').forEach((m) => m.remove());
        openEditor({
          key: entry.key,
          hit,
          onClose: () => {},
          onSaved: () => {
            const img = card.querySelector('img');
            const fresh = `${pictureUrl(entry.key)}?t=${Date.now()}`;
            if (img) {
              img.src = fresh;
            } else {
              card.querySelector('.card-img')!.innerHTML =
                `<img loading="lazy" alt="" src="${escapeAttr(fresh)}">`;
            }
            entry.picture = `${entry.key}.png`;
          },
        });
      },
    });
  }
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
