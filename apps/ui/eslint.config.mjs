import angularEslint from '@angular-eslint/eslint-plugin';
import baseConfig from '../../eslint.config.mjs';

export default [
    ...baseConfig,
    {
        files: ['**/*.ts'],
        plugins: {
            '@angular-eslint': angularEslint,
        },
        rules: {
            '@angular-eslint/directive-selector': [
                'error',
                {
                    type: 'attribute',
                    prefix: 'polaris',
                    style: 'camelCase',
                },
            ],
            '@angular-eslint/component-selector': [
                'error',
                {
                    type: 'element',
                    prefix: 'polaris',
                    style: 'kebab-case',
                },
            ],
            'import/extensions': [
                'error',
                'ignorePackages',
                {
                    js: 'never',
                    jsx: 'never',
                    ts: 'never',
                    tsx: 'never',
                },
            ],
            'no-shadow': 'off',
            '@typescript-eslint/no-shadow': ['error'],
            '@angular-eslint/prefer-standalone': 'off',
        },
    },
];
