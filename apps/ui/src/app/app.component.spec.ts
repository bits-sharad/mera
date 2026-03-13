import { HttpClientTestingModule } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { RouterTestingModule } from '@angular/router/testing';
import { OKTA_CONFIG, OktaAuthModule } from '@okta/okta-angular';
import { OktaAuth } from '@okta/okta-auth-js';

import { queryForElement } from '@jobmatchingmodelpoc/shared-utils-testing';

import AppComponent from './app.component';
import SharedModule from './shared/shared.module';
import environment from '../environments/environment';

describe('AppComponent', () => {
    beforeEach(async () => {
        const oktaAuth = new OktaAuth(environment.oktaConfig);

        await TestBed.configureTestingModule({
            imports: [RouterTestingModule, OktaAuthModule, SharedModule, HttpClientTestingModule],
            declarations: [AppComponent],
            providers: [{ provide: OKTA_CONFIG, useValue: { oktaAuth } }],
        }).compileComponents();
    });

    it('should create the app', () => {
        const fixture = TestBed.createComponent(AppComponent);
        const app = fixture.componentInstance;
        expect(app).toBeTruthy();
    });

    it("should have as title 'starter-app'", () => {
        const fixture = TestBed.createComponent(AppComponent);
        const app = fixture.componentInstance;
        expect(app.title).toBe('starter-app');
    });

    it('should correctly inject the okta dependency from the injection token', () => {
        const testOktaAuth = TestBed.inject(OKTA_CONFIG);
        const fixture = TestBed.createComponent(AppComponent);
        const oktaAuthDependency = fixture.debugElement.injector.get(OKTA_CONFIG);

        expect(oktaAuthDependency).toBeTruthy();
        expect(oktaAuthDependency).toBe(testOktaAuth);
    });

    it('should display API internal error', () => {
        const fixture = TestBed.createComponent(AppComponent);
        fixture.componentInstance.apiError = true;
        fixture.detectChanges();
        const compiled = fixture.nativeElement as HTMLElement;
        const errorBanner = queryForElement<HTMLDivElement>(compiled, '.main__api_error');
        expect(errorBanner).toBeTruthy();
        expect(errorBanner?.textContent).toContain('Tasks API error');
    });

    it('should display API unreachable error', () => {
        const fixture = TestBed.createComponent(AppComponent);
        fixture.componentInstance.apiUnreachable = true;
        fixture.detectChanges();
        const compiled = fixture.nativeElement as HTMLElement;
        const errorBanner = queryForElement<HTMLDivElement>(compiled, '.main__api_error');
        expect(errorBanner).toBeTruthy();
        expect(errorBanner?.textContent).toContain('Tasks API is unreachable');
    });
});
