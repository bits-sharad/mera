import { HttpRequest, HttpHandler, HttpEvent, HttpInterceptor } from '@angular/common/http';
import { Inject, Injectable } from '@angular/core';
import { OktaConfig, OKTA_CONFIG } from '@okta/okta-angular';
import { Observable } from 'rxjs';

/**
 * The interceptor is responsible for injecting the PKCE bearer token into the angular HTTP client,
 * This bearer token is intercepted and validated by API middleware within the NestJS application.
 * @see {@link OktaGuard} in the NestJS codebase for  more details on using the bearer token - especially {@link OktaGuard#getAuthToken}.
 */
@Injectable()
export default class AuthInterceptor implements HttpInterceptor {
    /**
     * Constructor for the interceptor.
     * @param {OktaConfig} oktaConfig - The OKTA Configuration.
     */
    constructor(@Inject(OKTA_CONFIG) private oktaConfig: OktaConfig) {}

    /**
     * Adds an Authorization header to the request if the request is to an allowed origin.
     * @param {HttpRequest<unknown>} request - The request to intercept.
     * @param {HttpHandler} next - The next HTTP handler in the chain.
     * @returns {Observable<HttpEvent<unknown>>} - The intercepted request, with an added Authorization header if applicable.
     */
    intercept(request: HttpRequest<unknown>, next: HttpHandler): Observable<HttpEvent<unknown>> {
        return next.handle(this.addAuthHeaderToAllowedOrigins(request));
    }

    /**
     * Interceptor to add bearer tokens to all requests performed from angular.
     * @param {HttpRequest} request - HTTP request object to add headers to.
     * @returns {HttpRequest} - request with auth headers embedded.
     */
    private addAuthHeaderToAllowedOrigins(request: HttpRequest<unknown>): HttpRequest<unknown> {
        let req = request;
        const authToken = this.oktaConfig.oktaAuth.getAccessToken();
        if (authToken) {
            req = request.clone({ setHeaders: { Authorization: `Bearer ${authToken}` } });
        }
        return req;
    }
}

export const isTestEnvironment = Boolean('Cypress' in window);
