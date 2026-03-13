import path from 'node:path';
import { fileURLToPath } from 'node:url';
import js from '@eslint/js';
import { FlatCompat } from '@eslint/eslintrc';
import { fixupConfigRules } from '@eslint/compat';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const compat = new FlatCompat({
    baseDirectory: __dirname,
    recommendedConfig: js.configs.recommended,
    allConfig: js.configs.all,
});

export default [
    {
        ignores: ['**/coverage/', '**/dist/', '**/node_modules/', '**/_cicd/', '**/.venv/'],
    },
    ...fixupConfigRules(compat.extends('@mmctech-artifactory/polaris-base')),
    {
        files: ['**/*.ts', '**/*.tsx', '**/*.js', '**/*.jsx'],

        rules: {
            '@typescript-eslint/no-explicit-any': 'warn',
            // Override deprecated TypeScript ESLint rules that have been removed or renamed
            '@typescript-eslint/lines-between-class-members': 'off',
            'lines-between-class-members': ['error', 'always'],
            '@typescript-eslint/no-throw-literal': 'off',
            'no-throw-literal': 'error',
            '@typescript-eslint/no-empty-object-type': 'off',
            '@typescript-eslint/ban-types': 'off',
            'jsdoc/require-jsdoc': [
                'warn',
                {
                    require: {
                        MethodDefinition: true,
                    },
                },
            ],
        },
    },
];
