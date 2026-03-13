/* eslint-disable @typescript-eslint/no-explicit-any */
import { NO_ERRORS_SCHEMA } from '@angular/core';
import { TestBed, ComponentFixture } from '@angular/core/testing';
import { Router } from '@angular/router';
import { RouterTestingModule } from '@angular/router/testing';
import { OKTA_AUTH, OKTA_CONFIG } from '@okta/okta-angular';
import { OktaAuth } from '@okta/okta-auth-js';
import { MockProxy, mock } from 'jest-mock-extended';

import OktaCallbackComponent from './okta-callback.component';

let component: OktaCallbackComponent;
let fixture: ComponentFixture<OktaCallbackComponent>;
let oktaAuth: OktaAuth;
let originalLocation: Location;
let mockRouter: MockProxy<Router>;
beforeEach(() => {
    originalLocation = window.location;
    // Create a complete mock location object
    const mockLocation = {
        protocol: 'https:',
        hostname: originalLocation.hostname,
        port: originalLocation.port,
        pathname: originalLocation.pathname,
        search: '?code=fake',
        hash: originalLocation.hash,
        href: 'https://foo',
        origin: originalLocation.origin,
        host: originalLocation.host,
        replace: jest.fn(),
        assign: jest.fn(),
        reload: jest.fn(),
        toString: jest.fn(() => 'https://foo'),
    };
    // Replace the entire window.location object
    delete (window as any).location;
    (window as any).location = mockLocation;
});
afterEach(() => {
    // Restore the original location object
    delete (window as any).location;
    (window as any).location = originalLocation;
});

/**
 *
 *bootstrap - configures the testing module for the OktaCallbackComponent.
 * @param {object} [config] - configuration object for the OKTA_CONFIG provider.
 * @param {boolean} [isLoginRedirectTrue] - sets the login redirect to property in okta configuration
 */
function bootstrap(config = {}, isLoginRedirectTrue = true) {
    oktaAuth = {
        handleRedirect: jest.fn(),
        isLoginRedirect: jest.fn().mockReturnValue(isLoginRedirectTrue),
        idx: { isInteractionRequiredError: jest.fn().mockReturnValue(true) },
    } as unknown as OktaAuth;
    mockRouter = mock<Router>();
    TestBed.configureTestingModule({
        imports: [RouterTestingModule.withRoutes([{ path: 'foo', redirectTo: '/foo' }])],
        declarations: [OktaCallbackComponent],
        schemas: [NO_ERRORS_SCHEMA],
        providers: [
            {
                provide: OKTA_CONFIG,
                useValue: config,
            },

            {
                provide: OKTA_AUTH,
                useValue: oktaAuth,
            },
            {
                provide: Router,
                useValue: mockRouter,
            },
        ],
    });
    fixture = TestBed.createComponent(OktaCallbackComponent);
    component = fixture.componentInstance;
}

describe('OktaCallbackComponent', () => {
    it('should create the component', async () => {
        bootstrap();
        expect(component).toBeTruthy();
    });

    it('should call handleRedirect', async () => {
        bootstrap();
        jest.spyOn(oktaAuth, 'handleRedirect').mockReturnValue(Promise.resolve());
        fixture.detectChanges();
        expect(oktaAuth.handleRedirect).toHaveBeenCalled();
    });

    it('catches errors from handleRedirect', async () => {
        bootstrap();
        const error = new Error('test error');
        jest.spyOn(oktaAuth, 'handleRedirect').mockReturnValue(Promise.reject(error));
        fixture.detectChanges();
        expect(oktaAuth.handleRedirect).toHaveBeenCalled();
        await fixture.whenStable();
        expect(component.error).toBe('Error: test error');
    });
});

describe('interaction code flow', () => {
    it('will call `onAuthResume` function, if defined', async () => {
        const onAuthResume = jest.fn();
        bootstrap({ onAuthResume });
        const error = new Error('my fake error');
        jest.spyOn(oktaAuth, 'handleRedirect').mockReturnValue(Promise.reject(error));

        fixture.detectChanges();
        await fixture.whenStable();
        expect(oktaAuth.idx.isInteractionRequiredError).toHaveBeenCalledWith(error);
        expect(onAuthResume).toHaveBeenCalledWith(oktaAuth, (component as any).injector);
        expect(component.error).toBeUndefined();
    });
});

it('will call `onAuthRequired` function, if `onAuthResume` is not defined', async () => {
    const onAuthRequired = jest.fn();
    bootstrap({ onAuthRequired });
    const error = new Error('my fake error');
    jest.spyOn(oktaAuth, 'handleRedirect').mockReturnValue(Promise.reject(error));

    fixture.detectChanges();
    await fixture.whenStable();
    expect(oktaAuth.idx.isInteractionRequiredError).toHaveBeenCalledWith(error);
    expect(onAuthRequired).toHaveBeenCalledWith(oktaAuth, (component as any).injector);
    expect(component.error).toBeUndefined();
});

it('if neither `onAuthRequired` or `onAuthResume` are defined, the error is displayed', async () => {
    bootstrap();
    const error = new Error('my fake error');
    jest.spyOn(oktaAuth, 'handleRedirect').mockReturnValue(Promise.reject(error));

    fixture.detectChanges();
    await fixture.whenStable();
    expect(oktaAuth.idx.isInteractionRequiredError).toHaveBeenCalledWith(error);
    expect(component.error).toBe('Error: my fake error');
});

it('should call navgiate redirect if isLoginRedirect returns false', async () => {
    bootstrap({}, false);
    fixture.detectChanges();
    await fixture.whenStable();
    expect(mockRouter.navigate).toHaveBeenCalledWith(['/']);
});
