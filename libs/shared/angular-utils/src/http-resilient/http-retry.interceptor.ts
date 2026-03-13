import { HttpEvent, HttpHandler, HttpInterceptor, HttpRequest } from '@angular/common/http';
import { Inject, Injectable } from '@angular/core';
import { Observable, of, throwError, timer } from 'rxjs';
import { mergeMap, retryWhen, tap } from 'rxjs/operators';

import ResilientHttpConfig from './http-resilient-config';
import { calculateRetryDelay, getParsedResilientHttpConfig } from './http-service';

@Injectable()
export default class HttpRetryInterceptor implements HttpInterceptor {
    static HTTP_RETRY_CONFIG = 'HTTP_RETRY_CONFIG';

    /**
     * Constructor for the interceptor.
     * @param {ResilientHttpConfig} httpRetryConfig - The http retry configuration.
     */
    constructor(@Inject('HTTP_RETRY_CONFIG') private httpRetryConfig: ResilientHttpConfig) {}

    /**
     * Retries the request if the request is of a specified method in the http retry configuration and the response status is a failure status
     * @param {HttpRequest<unknown>} request - The request to intercept.
     * @param {HttpHandler} next - The next HTTP handler in the chain.
     * @returns {Observable<HttpEvent<unknown>>} - The intercepted request, with retry logic applied if applicable.
     */
    intercept(request: HttpRequest<unknown>, next: HttpHandler): Observable<HttpEvent<unknown>> {
        const retryConfig = getParsedResilientHttpConfig(this.httpRetryConfig, request.url);
        if (retryConfig.methods.includes(request.method)) {
            return next.handle(request).pipe(this.retryAfterDelay(retryConfig));
        }
        return next.handle(request);
    }

    /**
     * Adds a mechanism to retry a request if failed as a part of resiliency.
     * @param {object} retryConfig - an object with retry config.
     * @returns {Observable} The retry operator that can be used to retry failed requests.
     */
    // eslint-disable-next-line
    retryAfterDelay(retryConfig: any): any {
        return retryWhen((errors) =>
            errors.pipe(
                mergeMap((err, count) => {
                    if (
                        retryConfig.responseStatusCodes.includes(err.status) &&
                        count !== retryConfig.retries
                    ) {
                        return of(err).pipe(
                            tap((error: { url: string }) =>
                                console.warn(
                                    `Retrying ${error.url}. Retry count ${
                                        count + 1
                                    }, delay:  ${calculateRetryDelay(
                                        retryConfig.exponent,
                                        count,
                                        retryConfig.retryDelayMs
                                    )}`
                                )
                            ),
                            mergeMap(() =>
                                timer(
                                    calculateRetryDelay(
                                        retryConfig.exponent,
                                        count,
                                        retryConfig.retryDelayMs
                                    )
                                )
                            )
                        );
                    }
                    return throwError(err);
                })
            )
        );
    }
}
