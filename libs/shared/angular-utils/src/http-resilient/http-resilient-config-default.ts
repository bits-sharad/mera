/**
 * Represents the default config entry in the ResilientHttpConfig.
 */
export default interface ResilientHttpConfigDefault {
    methods: Array<string>;
    retries: number;
    retryDelayMs: number;
    responseStatusCodes: Array<number>;
    exponent: number;
}
