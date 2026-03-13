import angularEslint from '@angular-eslint/eslint-plugin';
import baseConfig from '../../../eslint.config.mjs';

export default [
    ...baseConfig,
    {
        files: ['**/*.ts'],
        plugins: {
            '@angular-eslint': angularEslint,
        },
        rules: {
            // Angular-specific rules for component/directive selectors
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
            '@angular-eslint/prefer-standalone': 'off',
        },
    },
    {
        files: ['**/*.html'],
        rules: {},
    },
];
