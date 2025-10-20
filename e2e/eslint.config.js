import js from '@eslint/js';
import tsParser from '@typescript-eslint/parser';
import tsPlugin from '@typescript-eslint/eslint-plugin';

export default [
  js.configs.recommended,
  {
    files: ['tests/**/*.ts'],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        ecmaVersion: 2020,
        sourceType: 'module',
        project: './tsconfig.json',
      },
      globals: {
        console: 'readonly',
        process: 'readonly',
        Buffer: 'readonly',
        document: 'readonly',
      },
    },
    plugins: {
      '@typescript-eslint': tsPlugin,
    },
    rules: {
      // TypeScript rules - relaxed for tests
      '@typescript-eslint/no-unused-vars': [
        'warn',
        {
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_',
          caughtErrorsIgnorePattern: '^_',
        },
      ],
      '@typescript-eslint/no-explicit-any': 'warn',
      '@typescript-eslint/no-inferrable-types': 'off',

      // General rules - relaxed for tests
      'no-console': 'off',
      'prefer-const': 'warn',
      'no-var': 'error',
      'object-shorthand': 'off',
      'prefer-template': 'off',
      'no-unused-vars': 'off', // Use TypeScript version instead

      // Playwright-specific - allow common patterns
      'no-await-in-loop': 'off', // Common in E2E tests
      'no-empty': 'warn',
      'no-unreachable': 'error',

      // Code style - relaxed
      'comma-dangle': 'off',
      quotes: 'off',
      semi: 'off',
    },
  },
  {
    // Ignore compiled files and reports
    ignores: [
      'node_modules/',
      'test-results/',
      'playwright-report/',
      '*.js',
      '*.d.ts',
    ],
  },
];
