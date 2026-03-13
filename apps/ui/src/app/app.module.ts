import { HTTP_INTERCEPTORS, provideHttpClient, withInterceptorsFromDi } from '@angular/common/http';
import { CUSTOM_ELEMENTS_SCHEMA, NgModule } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { BrowserModule } from '@angular/platform-browser';
import { OKTA_CONFIG, OktaAuthModule } from '@okta/okta-angular';
import { delay, OktaAuth, TokenManagerError } from '@okta/okta-auth-js';

import AngularUtilsModule from '@jobmatchingmodelpoc/shared-angular-utils/angular-utils.module';
import AuthInterceptor from '@jobmatchingmodelpoc/shared-angular-utils/auth/auth.interceptor';
import HttpRetryConfig from '@jobmatchingmodelpoc/shared-angular-utils/http-resilient/http-retry.config';
import HttpRetryInterceptor from '@jobmatchingmodelpoc/shared-angular-utils/http-resilient/http-retry.interceptor';

import AppRoutingModule from './app-routing.module';
import AppComponent from './app.component';
import GalleryComponent from './features/gallery/gallery.component';
import TaskManagementService from './features/task-management/services/task-management.service';
import OktaCallbackComponent from './okta-callback/okta-callback.component';
import SharedModule from './shared/shared.module';
import environment from '../environments/environment';

const oktaAuth = new OktaAuth(environment.oktaConfig);

// Resolves a known issue with Okta by initiating a new login flow.
// Stale/Invalid sessions resulting in OAuthError "The client specified not to prompt, but the user isn't signed in."
oktaAuth.tokenManager.on('error', async (err: TokenManagerError) => {
    if (err.errorCode === 'login_required') {
        console.log('OAuthError: Caught known error with Okta sessions');
        console.log(err.message);
        await delay(1_000);
        oktaAuth.signInWithRedirect();
    }
});

@NgModule({
    declarations: [AppComponent, OktaCallbackComponent, GalleryComponent],
    bootstrap: [AppComponent],
    imports: [
        AppRoutingModule,
        BrowserModule,
        FormsModule,
        OktaAuthModule,
        SharedModule,
        AngularUtilsModule,
    ],
    providers: [
        { provide: OKTA_CONFIG, useValue: { oktaAuth } },
        { provide: HttpRetryInterceptor },
        { provide: HttpRetryInterceptor.HTTP_RETRY_CONFIG, useValue: HttpRetryConfig },
        { provide: HTTP_INTERCEPTORS, useClass: AuthInterceptor, multi: true },
        TaskManagementService,
        provideHttpClient(withInterceptorsFromDi()),
    ],
    schemas: [CUSTOM_ELEMENTS_SCHEMA],
})
export default class AppModule {}
