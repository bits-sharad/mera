// This file can be replaced during build by using the `fileReplacements` array.
// `ng build` replaces `environment.ts` with `environment.prod.ts`.
// The list of file replacements can be found in `angular.json`.

// TODO: Uncomment and fix import when run as part of the tests.

// import packageInfo  from '../../../../package.json';
// The client ID value is not sensitive. No values in the environment.ts files can be sensitive as these files are loaded into a user's web browser.
// This client ID value only gets used for local development (unlike environment.prod.ts which is used in the dev/prod-preview/prod envs).
// The values in environment.prod.ts get replaced with values from Vault by the Entrypoint script. We can't use the Entrypoint script locally because it needs to connect to Vault using Kubernetes auth (which we can't do locally).
// If we want this find/replace on the environment.ts, we'll need a different mechanism.
// Ultimately this only removes the value from the repo, anyone that goes to the deployed Blueprint site will be able to look at the source code and get this value.
const environment = {
    appVersion: '0.0.1',
    production: false,
    apiBaseUrl: 'http://localhost:8080/api/v1',
    // Required values for configuring the Okta SDK (https://github.com/okta/okta-auth-js#configuration-options)
    oktaConfig: {
        clientId: 'S5kAd3p0LVAr18s98yAs5gVFmhBxtmQdr6IACkaUfujxxGG9',
        issuer: 'https://mmc-bedford-int-non-prod-ingress.mgti.mmc.com/authentication/v1',
        redirectUri: 'http://localhost:4200/login/callback',
        scopes: [],
        pkce: true,
        postLogoutUri: 'http://localhost:4200',
    },
    oktaSignInConfig: {
        baseUrl: 'https://mmc-bedford-int-non-prod-ingress.mgti.mmc.com',
        clientId: 'S5kAd3p0LVAr18s98yAs5gVFmhBxtmQdr6IACkaUfujxxGG9',
        redirectUri: 'http://localhost:4200/login/callback',
    },
};

export default environment;
/*
 * For easier debugging in development mode, you can import the following file
 * to ignore zone related error stack frames such as `zone.run`, `zoneDelegate.invokeTask`.
 *
 * This import should be commented out in production mode because it will have a negative impact
 * on performance if an error is thrown.
 */
// import 'zone.js/plugins/zone-error';  // Included with Angular CLI.
