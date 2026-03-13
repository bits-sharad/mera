import { HttpClient, HttpErrorResponse, HTTP_INTERCEPTORS } from '@angular/common/http';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { fakeAsync, TestBed, tick } from '@angular/core/testing';
import { throwError } from 'rxjs';

import HttpRetryConfig from './http-retry.config';
import HttpRetryInterceptor from './http-retry.interceptor';
import * as httpService from './http-service';

describe('HttpConfigInterceptor', () => {
    let httpTestingController: HttpTestingController;
    let interceptor: HttpRetryInterceptor;
    let httpClient: HttpClient;

    beforeEach(() => {
        TestBed.configureTestingModule({
            imports: [HttpClientTestingModule],
            providers: [
                HttpRetryInterceptor,
                // register our interceptor with the testing module
                {
                    provide: HTTP_INTERCEPTORS,
                    useClass: HttpRetryInterceptor,
                    multi: true,
                },
                { provide: 'HTTP_RETRY_CONFIG', useValue: HttpRetryConfig },
            ],
        });
        interceptor = TestBed.inject(HttpRetryInterceptor);
        httpClient = TestBed.inject(HttpClient);
        httpTestingController = TestBed.inject(HttpTestingController);
    });

    afterEach(() => {
        // After every test, assert that there are no more pending requests.
        httpTestingController.verify();
        jest.resetAllMocks();
    });

    it('should be created', () => {
        expect(interceptor).toBeTruthy();
    });

    it('should retry 3 times when 404 error is encountered and default retries is set to 3', fakeAsync(() => {
        const testUrl = 'http://github.com';
        const errorMsg = '404 error';
        jest.spyOn(global.console, 'warn');
        httpClient.get(testUrl).subscribe(
            () => throwError('should have failed with the 404 error'),
            (error: HttpErrorResponse) => {
                expect(error.status).toBe(404);
                expect(error.error).toEqual(errorMsg);
            }
        );
        const retry = 3;
        for (let i = 0, c = retry + 1; i < c; i += 1) {
            const req = httpTestingController.expectOne(testUrl);
            req.flush(errorMsg, { status: 404, statusText: 'Not Found' });
            tick(1000);
        }
    }));

    it('should retry only first time when error occurs', fakeAsync(() => {
        const testUrl = 'http://github.com';
        const errorMsg = '404 error';
        jest.spyOn(global.console, 'warn');
        httpClient.get(testUrl).subscribe(
            () => throwError('should have failed with the 404 error'),
            (error: HttpErrorResponse) => {
                expect(error.status).toBe(404);
                expect(error.error).toEqual(errorMsg);
            }
        );
        const req = httpTestingController.expectOne(testUrl);
        req.flush(errorMsg, { status: 404, statusText: 'Not Found' });
        tick(1000);
        const firstRetry = httpTestingController.expectOne(testUrl);
        firstRetry.flush({ status: 200, statusText: 'ok' });
        expect(global.console.warn).toHaveBeenCalledTimes(1);
    }));

    it('should not retry when request is successful', fakeAsync(() => {
        const testUrl = 'http://github.com';
        jest.spyOn(global.console, 'warn');
        httpClient.get(testUrl).subscribe(() => {});
        const req = httpTestingController.expectOne(testUrl);
        req.flush({ status: 200, statusText: 'ok' });
        tick(1000);
        expect(global.console.warn).not.toHaveBeenCalled();
    }));

    it('should not retry when error is encountered and retries parameter in configuration is set 0', fakeAsync(() => {
        const testUrl = 'https://api.github.com';
        const errorMsg = '404 error';
        jest.spyOn(global.console, 'warn');
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
                    retries: 0,
                    retryDelayMs: 500,
                    responseStatusCodes: [401, 403, 404, 500],
                    exponent: 1,
                },
            ],
        };
        jest.spyOn(httpService, 'getParsedResilientHttpConfig').mockReturnValue(
            suppliedConfig.overrides[0] as never
        );

        httpClient.get(testUrl).subscribe(
            () => throwError('should have failed with the 404 error'),
            (error: HttpErrorResponse) => {
                expect(error.status).toBe(404);
                expect(error.error).toEqual(errorMsg);
            }
        );
        const req = httpTestingController.expectOne(testUrl);
        req.flush({ status: 200, statusText: 'ok' });
        tick(1000);
        expect(global.console.warn).not.toHaveBeenCalled();
    }));

    it('should not retry when request is passed and retries parameter in configuration is set 0', fakeAsync(() => {
        const testUrl = 'https://api.github.com';
        jest.spyOn(global.console, 'warn');
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
                    retries: 0,
                    retryDelayMs: 500,
                    responseStatusCodes: [401, 403, 404, 500],
                    exponent: 1,
                },
            ],
        };
        jest.spyOn(httpService, 'getParsedResilientHttpConfig').mockReturnValue(
            suppliedConfig.overrides[0] as never
        );
        httpClient.get(testUrl).subscribe(() => {});
        const req = httpTestingController.expectOne(testUrl);
        req.flush({ status: 200, statusText: 'ok' });
        tick(1000);
        expect(global.console.warn).not.toHaveBeenCalled();
    }));
});
