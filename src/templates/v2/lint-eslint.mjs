import js from '@eslint/js';
import { defineConfig } from 'eslint/config';
import tseslint from 'typescript-eslint';
import globals from 'globals';

export default defineConfig(
  { ignores: ['**/node_modules/**', '**/build/**', '**/dist/**', '**/local/**'] },
  {
    files: ['**/*.{js,cjs,mjs,jsx,ts,cts,mts,tsx}'],
    extends: [js.configs.recommended, tseslint.configs.recommended],
  },
  { files: ['**/*.{js,cjs,mjs,ts,cts,mts}'], languageOptions: { globals: globals.node } },
);
