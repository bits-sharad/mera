import { HttpClient, HTTP_INTERCEPTORS } from '@angular/common/http';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { fakeAsync, TestBed, tick } from '@angular/core/testing';
import { OktaConfig, OKTA_CONFIG } from '@okta/okta-angular';

import AuthInterceptor from './auth.interceptor';

const VERY_SECURE_TOKEN = '54432312';
describe('AuthInterceptor', () => {
    let httpMock: HttpTestingController;
    let authServiceStub: OktaConfig;
    let httpClient: HttpClient;

    beforeEach(() => {
        authServiceStub = {
            oktaAuth: {
                getAccessToken: () => VERY_SECURE_TOKEN,
            },
        } as unknown as OktaConfig;

        TestBed.configureTestingModule({
            imports: [HttpClientTestingModule],
            providers: [
                AuthInterceptor,
                {
                    provide: HTTP_INTERCEPTORS,
                    useClass: AuthInterceptor,
                    multi: true,
                },
                { provide: OKTA_CONFIG, useValue: authServiceStub },
            ],
        });

        httpClient = TestBed.inject(HttpClient);
        httpMock = TestBed.inject(HttpTestingController);
    });

    afterEach(() => {
        // After every test, assert that there are no more pending requests.
        httpMock.verify();
        jest.resetAllMocks();
    });
    it('should Append bearer token to HTTP requests', fakeAsync(() => {
        const testUrl = 'http://polaris-env';

        httpClient.get(testUrl).subscribe(() => {});
        const req = httpMock.expectOne(testUrl);
        req.flush({ status: 200, statusText: 'ok' });
        tick(1000);
        expect(
            // eslint-disable-next-line @typescript-eslint/dot-notation
            req.request.headers['lazyUpdate'].find((headers) => headers.name === 'Authorization')
                .value
        ).toBe(`Bearer ${VERY_SECURE_TOKEN}`);
    }));
});
