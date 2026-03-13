import { HttpClient } from '@angular/common/http';
import { Component, Injector } from '@angular/core';
import { OktaAuthStateService, OKTA_CONFIG } from '@okta/okta-angular';
import { OktaAuth } from '@okta/okta-auth-js';

import environment from '../environments/environment';

import('@mmctech/micro-lenai-webcomponent');

@Component({
    selector: 'polaris-root',
    templateUrl: './app.component.html',
    styleUrls: ['./app.component.scss'],
    standalone: false,
})
export default class AppComponent {
    title = 'starter-app';

    appVersion = environment.appVersion;

    currentYear = new Date().getFullYear();

    oktaAuth: OktaAuth;

    apiUnreachable = false;

    apiError = false;

    isMenuOpen = false;

    microLenAiApiUrl =
        'https://nasa-micro-lenai.int.prd.dal.oss2.mrshmc.com/api/v1/mmcdocs/response';

    /**
     *
     * @param {OktaAuthStateService} authStateService - service that provides the current state of the Okta authentication
     * @param {Injector} injector - service that provides the OktaAuth instance
     * @param {HttpClient} http - service for making HTTP requests
     */
    constructor(
        public authStateService: OktaAuthStateService,
        public injector: Injector,
        private http: HttpClient
    ) {
        // the OktaAuth instance is not directly available through the constructor dependency injection. Use the injector instead
        this.oktaAuth = injector.get(OKTA_CONFIG).oktaAuth;
        this.isAPILive();
    }

    /**
     * Check if API is up and running, updates the component state based on API response.
     */
    isAPILive(): void {
        const sub = this.http.get(`${environment.apiBaseUrl}/tasks`);
        sub.subscribe({
            next: () => {
                this.apiUnreachable = false;
                this.apiError = false;
            },
            error: (error) => {
                if (error.statusText === 'Unknown Error') this.apiUnreachable = true;
                if (error.statusText === 'Internal Server Error') this.apiError = true;
            },
        });
    }

    /**
     * Toggle Menu for Responsive Design
     */
    toggleMenu() {
        this.isMenuOpen = !this.isMenuOpen;
    }
}
