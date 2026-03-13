import ResilientHttpConfigDefault from './http-resilient-config-default';

export default interface ResilientHttpConfigOverride extends ResilientHttpConfigDefault {
    /**
     * The regular expressions to match against the request URL.
     */
    urlRegexes: Array<RegExp | string>;
}
