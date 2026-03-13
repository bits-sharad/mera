const { getJestProjectsAsync } = require('@nx/jest');

module.exports = async () => ({
    projects: await getJestProjectsAsync(),
    coverageThreshold: {
        global: {
            statements: 95,
            branches: 65,
            functions: 90,
            lines: 95,
        },
    },
});
