const HttpRetryConfig = {
    default: {
        methods: ['DELETE', 'GET', 'PATCH', 'POST', 'PUT'],
        retries: 3,
        retryDelayMs: 100,
        responseStatusCodes: [401, 403, 404, 500],
        exponent: 1,
    },
};

export default HttpRetryConfig;
