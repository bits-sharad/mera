/* eslint-disable no-template-curly-in-string */
// Vault stores the Okta config object as a string so we need to explicitly construct the object and Boolean values
const oktaConfig = JSON.parse('${{ UI_OKTA_CONFIG_ANGULAR }}');
const production = JSON.parse('${{ UI_PRODUCTION }}');
const baseUrl = new URL(oktaConfig.redirectUri);

baseUrl.hostname = window.location.hostname;
oktaConfig.redirectUri = baseUrl.href;
oktaConfig.postLogoutUri = `https://${window.location.hostname}`;
const environment = {
    appVersion: '${{ UI_APP_VERSION }}',
    production,
    apiBaseUrl: '${{ UI_API_BASE_URL }}',
    oktaConfig,
};

export default environment;
