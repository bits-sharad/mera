import { Component, OnInit, Optional, Injector, Inject } from '@angular/core';
import { Router } from '@angular/router';
import { OKTA_CONFIG, OktaConfig, OKTA_AUTH } from '@okta/okta-angular';
import { OktaAuth } from '@okta/okta-auth-js';

@Component({
    templateUrl: './okta-callback.component.html',
    styleUrls: ['./okta-callback.component.scss'],
    standalone: false,
})
export default class OktaCallbackComponent implements OnInit {
    accessDocs =
        'https://mmcglobal.sharepoint.com/sites/EnterpriseArchitecture/SitePages/How-to-Start.aspx#3.-okta-access';

    polarisDocs =
        'https://mmcglobal.sharepoint.com/sites/EnterpriseArchitecture/SitePages/polaris.aspx';

    error?: string;

    /**
     * @param {OktaConfig} config - The configuration object for the OKTA_CONFIG provider.
     * @param {OktaAuth} oktaAuth - The OKTA_AUTH provider.
     * @param {Router} router - Instance of Angular router
     * @param {Injector} [injector] - An optional Injector object.
     */
    constructor(
        @Inject(OKTA_CONFIG) private config: OktaConfig,
        @Inject(OKTA_AUTH) private oktaAuth: OktaAuth,
        private router: Router,
        @Optional() private injector?: Injector
    ) {}

    /**
     * Handles the callback from an Okta provider after a user has authenticated.
     * Attempts to parse code or tokens from the URL, store tokens in the TokenManager, and redirect back to the originalUri
     * using the oktaAuth.handleLoginRedirect() method. In case of an error, it checks if the error is an interaction required
     * error and if the injector is present. If both are true, it will call either the onAuthResume or onAuthRequired callback
     * function, passing in the oktaAuth and injector as arguments. If either of these callbacks is not present or if the error is
     * not an interaction required error, it will set the error property to the error message, and log the error to the console.
     * @returns {Promise<void>} - a promise that is resolved when the function completes.
     */
    async ngOnInit(): Promise<void> {
        // checks if current component state is redirected from oAuth flow or user has manually accessed the component straight from browser.
        if (this.oktaAuth.isLoginRedirect()) {
            try {
                // Parse code or tokens from the URL, store tokens in the TokenManager, and redirect back to the originalUri
                await this.oktaAuth.handleRedirect();
            } catch (e: unknown) {
                // Callback from social IDP. Show custom login page to continue.
                if (this.oktaAuth.idx.isInteractionRequiredError(e as Error) && this.injector) {
                    const { onAuthResume, onAuthRequired } = this.config;
                    const callbackFn = onAuthResume || onAuthRequired;
                    if (callbackFn) {
                        callbackFn(this.oktaAuth, this.injector);
                        return;
                    }
                }
                this.error = (e as Error).toString();

                // eslint-disable-next-line no-console
                console.warn(this.error);
            }
        } else {
            this.router.navigate(['/']);
        }
    }
}
