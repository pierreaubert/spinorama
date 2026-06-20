import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    include: ['src/headphone-image-editor/server/**/*.test.ts'],
    environment: 'node',
    globals: false,
    watch: false,
  },
});
