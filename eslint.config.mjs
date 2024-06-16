import js from '@eslint/js';
import eslintConfigPrettier from 'eslint-config-prettier';

import globals from 'globals';

export default [
    js.configs.recommended,
    {
        rules: {
            'no-unused-vars': 'error',
            'no-undef': 'warn',
        },
        languageOptions: {
            ecmaVersion: 'latest',
            sourceType: 'module',
            globals: {
                ...globals.browser,
            },
        },
    },
    eslintConfigPrettier,
];
