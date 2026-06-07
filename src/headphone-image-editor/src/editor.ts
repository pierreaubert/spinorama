import { proxiedImageUrl, savePicture, type ImageHit } from './api.ts';
import { removeBackground } from './bgremove.ts';

const OUTPUT_SIZE = 800;

export interface EditorOptions {
  key: string;
  hit: ImageHit;
  onClose: () => void;
  onSaved: () => void;
}

interface State {
  source: HTMLImageElement;
  /** Mask-applied RGBA pixels (only set after bg removal). */
  cleaned: ImageData | null;
  /** Logical scale: 1 = fit-contain at default. */
  scale: number;
  /** Center offset within the 800×800 canvas, in pixels. */
  offsetX: number;
  offsetY: number;
  bgRemoved: boolean;
}

export async function openEditor(opts: EditorOptions): Promise<void> {
  const root = renderShell(opts);
  document.body.append(root);

  const status = root.querySelector<HTMLElement>('[data-role=status]')!;
  const canvas = root.querySelector<HTMLCanvasElement>('[data-role=canvas]')!;
  const scaleInput = root.querySelector<HTMLInputElement>('[data-role=scale]')!;
  const bgToggle = root.querySelector<HTMLInputElement>('[data-role=bg-toggle]')!;
  const saveBtn = root.querySelector<HTMLButtonElement>('[data-role=save]')!;
  const closeBtn = root.querySelector<HTMLButtonElement>('[data-role=close]')!;

  const ctx = canvas.getContext('2d', { willReadFrequently: true })!;
  canvas.width = OUTPUT_SIZE;
  canvas.height = OUTPUT_SIZE;

  closeBtn.addEventListener('click', () => {
    root.remove();
    opts.onClose();
  });

  status.textContent = 'Downloading image…';
  const img = await loadImage(proxiedImageUrl(opts.hit.imageUrl));

  const state: State = {
    source: img,
    cleaned: null,
    scale: 1,
    offsetX: 0,
    offsetY: 0,
    bgRemoved: false,
  };

  setupPan(canvas, state, () => render(ctx, state));
  scaleInput.addEventListener('input', () => {
    state.scale = Number(scaleInput.value);
    render(ctx, state);
  });

  bgToggle.addEventListener('change', async () => {
    if (!bgToggle.checked) {
      state.bgRemoved = false;
      render(ctx, state);
      return;
    }
    if (!state.cleaned) {
      bgToggle.disabled = true;
      try {
        state.cleaned = await runBackgroundRemoval(img, (msg) => (status.textContent = msg));
      } catch (err) {
        status.textContent = `Background removal failed: ${(err as Error).message}`;
        bgToggle.checked = false;
        bgToggle.disabled = false;
        return;
      }
      bgToggle.disabled = false;
    }
    state.bgRemoved = true;
    status.textContent = 'Background removed.';
    render(ctx, state);
  });

  saveBtn.addEventListener('click', async () => {
    saveBtn.disabled = true;
    status.textContent = 'Saving…';
    try {
      const dataUrl = canvas.toDataURL('image/png');
      const result = await savePicture(opts.key, dataUrl);
      status.textContent = `Saved (${(result.bytes / 1024).toFixed(1)} kB).`;
      opts.onSaved();
      setTimeout(() => {
        root.remove();
        opts.onClose();
      }, 600);
    } catch (err) {
      status.textContent = `Save failed: ${(err as Error).message}`;
      saveBtn.disabled = false;
    }
  });

  status.textContent = 'Adjust framing, then save.';
  render(ctx, state);
}

function renderShell(opts: EditorOptions): HTMLElement {
  const wrap = document.createElement('div');
  wrap.className = 'modal';
  wrap.innerHTML = `
    <div class="editor">
      <header>
        <strong>${escapeHtml(opts.key)}</strong>
        <button data-role="close" type="button">Cancel</button>
      </header>
      <div class="editor-body">
        <canvas data-role="canvas"></canvas>
        <aside class="editor-controls">
          <label>
            <span>Scale</span>
            <input data-role="scale" type="range" min="0.2" max="2.5" step="0.01" value="1">
          </label>
          <label class="row">
            <input data-role="bg-toggle" type="checkbox">
            <span>Remove background</span>
          </label>
          <p class="hint">Drag the canvas to recenter the headphone. Output is PNG 800×800, transparent, fit-contain.</p>
          <button data-role="save" class="primary" type="button">Save &amp; replace</button>
          <p data-role="status" class="status"></p>
        </aside>
      </div>
    </div>
  `;
  return wrap;
}

function setupPan(canvas: HTMLCanvasElement, state: State, redraw: () => void): void {
  let dragging = false;
  let startX = 0;
  let startY = 0;
  let baseX = 0;
  let baseY = 0;
  canvas.addEventListener('pointerdown', (e) => {
    dragging = true;
    canvas.setPointerCapture(e.pointerId);
    startX = e.clientX;
    startY = e.clientY;
    baseX = state.offsetX;
    baseY = state.offsetY;
  });
  canvas.addEventListener('pointermove', (e) => {
    if (!dragging) return;
    const rect = canvas.getBoundingClientRect();
    const px2logical = OUTPUT_SIZE / rect.width;
    state.offsetX = baseX + (e.clientX - startX) * px2logical;
    state.offsetY = baseY + (e.clientY - startY) * px2logical;
    redraw();
  });
  canvas.addEventListener('pointerup', () => {
    dragging = false;
  });
  canvas.addEventListener('pointercancel', () => {
    dragging = false;
  });
}

function render(ctx: CanvasRenderingContext2D, state: State): void {
  ctx.clearRect(0, 0, OUTPUT_SIZE, OUTPUT_SIZE);
  // Light checkerboard background so transparency is visible.
  drawCheckerboard(ctx, OUTPUT_SIZE, OUTPUT_SIZE, 16);

  const sw = state.source.naturalWidth;
  const sh = state.source.naturalHeight;
  if (!sw || !sh) return;

  const fit = Math.min(OUTPUT_SIZE / sw, OUTPUT_SIZE / sh);
  const drawW = sw * fit * state.scale;
  const drawH = sh * fit * state.scale;
  const cx = OUTPUT_SIZE / 2 + state.offsetX;
  const cy = OUTPUT_SIZE / 2 + state.offsetY;
  const dx = cx - drawW / 2;
  const dy = cy - drawH / 2;

  if (state.bgRemoved && state.cleaned) {
    const off = document.createElement('canvas');
    off.width = state.cleaned.width;
    off.height = state.cleaned.height;
    off.getContext('2d')!.putImageData(state.cleaned, 0, 0);
    ctx.drawImage(off, dx, dy, drawW, drawH);
  } else {
    ctx.drawImage(state.source, dx, dy, drawW, drawH);
  }
}

function drawCheckerboard(
  ctx: CanvasRenderingContext2D,
  w: number,
  h: number,
  cell: number,
): void {
  for (let y = 0; y < h; y += cell) {
    for (let x = 0; x < w; x += cell) {
      const dark = (((x / cell) | 0) + ((y / cell) | 0)) % 2 === 0;
      ctx.fillStyle = dark ? '#e9eef3' : '#f7f9fc';
      ctx.fillRect(x, y, cell, cell);
    }
  }
}

async function runBackgroundRemoval(
  img: HTMLImageElement,
  onStatus: (s: string) => void,
): Promise<ImageData> {
  const w = img.naturalWidth;
  const h = img.naturalHeight;
  const c = document.createElement('canvas');
  c.width = w;
  c.height = h;
  const cctx = c.getContext('2d', { willReadFrequently: true })!;
  cctx.drawImage(img, 0, 0);
  const src = cctx.getImageData(0, 0, w, h);
  return removeBackground(src, onStatus);
}

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error(`Failed to load ${src}`));
    img.src = src;
  });
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
