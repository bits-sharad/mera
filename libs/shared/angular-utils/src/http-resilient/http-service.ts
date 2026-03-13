import ResilientHttpConfig from './http-resilient-config';
import ResilientHttpConfigDefault from './http-resilient-config-default';
import HttpRetryConfig from './http-retry.config';

/**
 * Returns the override object if it matches the request url
 * @param {ResilientHttpConfig} httpResilientConfig The override array
 * @param {string} url The requested url by the user
 * @returns {ResilientHttpConfig} The config which matches the requested url.
 */
export function getMatchingHttpConfigByUrl(
    httpResilientConfig: ResilientHttpConfig,
    url: string
): ResilientHttpConfigDefault {
    /* eslint-disable  @typescript-eslint/no-explicit-any */
    let config: any = httpResilientConfig.default;
    if (httpResilientConfig.overrides) {
        // eslint-disable-next-line no-restricted-syntax
        for (const element of httpResilientConfig.overrides) {
            const isMatches = element.urlRegexes.some((urlRegex) => {
                const regex = new RegExp(urlRegex);
                return regex.test(url);
            });
            if (isMatches) {
                config = element;
                break;
            }
        }
    }
    return config as ResilientHttpConfigDefault;
}

/**
 * Calculates and returns the delay (in milliseconds) to use between retries. When the
 * exponent is greater than 1, an delay is calculated which increases exponentially
 * as the retryNumber increases. In all other cases, the initialIntervalMs is returned.
 * @param {number} exponent The exponent to use when calculating retries for use with exponential back-off.
 * @param {number} retryNumber The current retry number.
 * @param {number} initialInterval The initial interval to use between retries (in milliseconds).
 * @returns {number} The retry delay to use (in milliseconds).
 */
export function calculateRetryDelay(
    exponent: number,
    retryNumber: number,
    initialInterval: number
): number {
    if (exponent <= 1) return initialInterval;
    return exponent ** retryNumber * initialInterval;
}

/**
 * Returns the library default resilient HTTP configuration to use.
 * @returns {ResilientHttpConfig} The library default configuration.
 */
export function getDefaultResilientHttpConfig(): ResilientHttpConfig {
    return HttpRetryConfig;
}

/**
 * When no default is provided in the supplied config, the library default is used. It returns
 * configured default when it is available in the library
 * @param {ResilientHttpConfig} resilientHttpConfig The resilient HTTP config to be parsed.
 * @param {url} url The URL to retry.
 * @returns {object} The parsed resilient HTTP config.
 */
export function getParsedResilientHttpConfig(
    resilientHttpConfig: ResilientHttpConfig,
    url: string
): ResilientHttpConfigDefault {
    let retryConfig = getDefaultResilientHttpConfig().default as ResilientHttpConfigDefault;
    if (resilientHttpConfig && Object.keys(resilientHttpConfig).length !== 0) {
        const config = getMatchingHttpConfigByUrl(resilientHttpConfig, url);
        // When there is either no config, or the config has no defaults set, use our own defaults.
        if (config) retryConfig = config as ResilientHttpConfigDefault;
    }
    return retryConfig as ResilientHttpConfigDefault;
}
