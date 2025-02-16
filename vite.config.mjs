/// <reference types="vitest" />
import { configDefaults, defineConfig } from 'vitest/config';

export default defineConfig({
    test: {
        include: ['**/src/website/*.test.js', '**/tests/*.test.js'],
        exclude: [...configDefaults.exclude, '**/dist/**', '**/build/**'],
        watch: false,
        environment: 'jsdom',
    },
});
