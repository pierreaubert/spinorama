import './styles.css';
import { mountGrid } from './grid.ts';

const root = document.querySelector<HTMLElement>('#app');
if (!root) {
  throw new Error('#app not found');
}
mountGrid(root).catch((err) => {
  console.error(err);
  root.innerHTML = `<p class="status error">${(err as Error).message}</p>`;
});
