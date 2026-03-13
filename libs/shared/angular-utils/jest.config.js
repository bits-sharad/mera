const esModules = ['@angular'];

module.exports = {
    displayName: 'angular-utils',
    preset: '../../../jest.preset.js',
    setupFilesAfterEnv: ['<rootDir>/test-setup.ts'],
    globals: {
        'ts-jest': {
            tsconfig: '<rootDir>/tsconfig.spec.json',
        },
    },
    coverageDirectory: '../../../coverage/libs/shared/angular-utils',
    transform: {
        '^.+.(ts|mjs|js|html)$': 'jest-preset-angular',
    },
    transformIgnorePatterns: [`<rootDir>/node_modules/(?!.*\\.mjs$|${esModules.join('|')})`],
    snapshotSerializers: [
        'jest-preset-angular/build/serializers/no-ng-attributes',
        'jest-preset-angular/build/serializers/ng-snapshot',
        'jest-preset-angular/build/serializers/html-comment',
    ],
};
