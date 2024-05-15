/// <reference types="vitest" />
import { configDefaults, defineConfig } from 'vitest/config'

export default defineConfig({
    test: {
        include: ['**/src/website/*.test.js', '**/tests/*.test.js'],
	exclude: [...configDefaults.exclude, '**/docs/**', '**/build/**'],
	watch: false,
	environment: "jsdom"
    }
})
