import { getParsedResilientHttpConfig, calculateRetryDelay } from './http-service';
import * as httpService from './http-service';

describe('getParsedResilientHttpConfig', () => {
    it('returns the library default config when an empty config is supplied', () => {
        const libraryDefaultConfig = getParsedResilientHttpConfig(undefined, undefined);
        const expectedResult = {
            default: {
                methods: ['DELETE', 'GET', 'PATCH', 'POST', 'PUT'],
                retries: 3,
                retryDelayMs: 100,
                responseStatusCodes: [401, 403, 404, 500],
                exponent: 1,
            },
        };
        expect(libraryDefaultConfig).toEqual(expectedResult.default);
    });

    it('returns the supplied config when it contains a valid default config', () => {
        const suppliedConfig = {
            default: {
                methods: ['GET'],
                retries: 2,
                retryDelayMs: 500,
                responseStatusCodes: [401, 403, 404, 500],
                exponent: 1,
            },
        };
        const parsedConfig = getParsedResilientHttpConfig(suppliedConfig, 'https://www.github.com');
        expect(parsedConfig).toEqual(suppliedConfig.default);
    });

    it('returns the supplied overrides and library defaults when the supplied config has no defaults', () => {
        const suppliedConfig = {
            overrides: [
                {
                    urlRegexes: [/api\.github\.com/],
                    methods: ['GET'],
                    retries: 2,
                    retryDelayMs: 500,
                    responseStatusCodes: [401, 403, 404, 500],
                    exponent: 1,
                },
                {
                    urlRegexes: [/api\.ado\.com/],
                    methods: ['POST', 'PUT'],
                    retries: 4,
                    retryDelayMs: 2000,
                    responseStatusCodes: [500],
                    exponent: 2,
                },
            ],
        };

        const parsedConfig = getParsedResilientHttpConfig(suppliedConfig, 'https://api.github.com');
        expect(parsedConfig).toEqual(suppliedConfig.overrides[0]);
    });

    it('returns the supplied overrides as http config when both overrides and defaults specified', () => {
        const suppliedConfig = {
            default: {
                methods: ['GET', 'PUT'],
                retries: 2,
                retryDelayMs: 1500,
                responseStatusCodes: [401, 403, 404, 500],
                exponent: 1,
            },
            overrides: [
                {
                    urlRegexes: [/api\.github\.com/],
                    methods: ['GET'],
                    retries: 2,
                    retryDelayMs: 500,
                    responseStatusCodes: [401, 403, 404, 500],
                    exponent: 1,
                },
                {
                    urlRegexes: [/api\.ado\.com/],
                    methods: ['POST', 'PUT'],
                    retries: 4,
                    retryDelayMs: 2000,
                    responseStatusCodes: [500],
                    exponent: 2,
                },
                {
                    urlRegexes: [/api\.github\.com/],
                    methods: ['GET'],
                    retries: 2,
                    retryDelayMs: 500,
                    responseStatusCodes: [401, 403, 404, 500],
                    exponent: 0,
                },
            ],
        };

        const parsedConfig = getParsedResilientHttpConfig(suppliedConfig, 'https://api.github.com');
        expect(parsedConfig).toEqual(suppliedConfig.overrides[0]);
    });

    it('returns default when requested url does not match the supplied config', () => {
        const suppliedConfig = {
            default: {
                methods: ['GET', 'PUT'],
                retries: 2,
                retryDelayMs: 1500,
                responseStatusCodes: [401, 403, 404, 500],
                exponent: 1,
            },
            overrides: [
                {
                    urlRegexes: [/test\.github\.com/],
                    methods: ['GET'],
                    retries: 2,
                    retryDelayMs: 500,
                    responseStatusCodes: [401, 403, 404, 500],
                    exponent: 1,
                },
            ],
        };

        jest.spyOn(httpService, 'getMatchingHttpConfigByUrl').mockReturnValue(undefined);
        const parsedConfig = getParsedResilientHttpConfig(suppliedConfig, 'https://api.github.com');
        expect(parsedConfig).toEqual(suppliedConfig.default);
    });

    describe('calculateRetryDelay', () => {
        it('returns the initialInterval when the exponent = 0', () => {
            const initialInterval = 1000;
            const exponent = 0;
            const retryDelay = calculateRetryDelay(exponent, 1, initialInterval);
            expect(retryDelay).toEqual(initialInterval);
        });
        it('returns the initialInterval when the exponent = 1', () => {
            const initialInterval = 1000;
            const exponent = 1;
            const retryDelay = calculateRetryDelay(exponent, 1, initialInterval);
            expect(retryDelay).toEqual(initialInterval);
        });

        it('uses the exponent when its value is > 1', () => {
            const initialInterval = 1000;
            const exponent = 2;

            const retry1Delay = calculateRetryDelay(exponent, 1, initialInterval);
            const retry2Delay = calculateRetryDelay(exponent, 2, initialInterval);
            const retry3Delay = calculateRetryDelay(exponent, 3, initialInterval);

            expect(retry1Delay).toBe(2000);
            expect(retry2Delay).toBe(4000);
            expect(retry3Delay).toBe(8000);
        });
    });
});
