/* eslint-disable import/no-import-module-exports */
import { defineConfig } from 'cypress';

import setupNodeEvents from './src/plugins/index';

module.exports = defineConfig({
    defaultCommandTimeout: 100000,
    e2e: {
        fileServerFolder: '.',
        fixturesFolder: './src/fixtures',
        specPattern: './src/integration/*.ts',
        modifyObstructiveCode: false,
        setupNodeEvents,
        supportFile: './src/support/index.ts',
        video: false,
        videosFolder: '../../dist/cypress/apps/ui-e2e/videos',
        screenshotsFolder: '../../dist/cypress/apps/ui-e2e/screenshots',
        chromeWebSecurity: false,
        env: { tsConfig: 'tsconfig.json' },
    },
} as Cypress.ConfigOptions);
