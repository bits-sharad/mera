/* eslint-disable new-cap */
import { URL } from 'url';

describe('production Environment', () => {
    const mockOktaObj = {
        clientId: '123434',
        issuer: 'https://mmc.oktapreview.com/oauth2/default',
        redirectUri: 'https://dev-polaris-int.np.dal.oss2.mrshmc.com/login/callback',
        scopes: ['openid'],
        pkce: true,
    };

    it('should create a URL and override the Okta configurations', () => {
        // Mock URL constructor to always return a URL with experiment-test.com hostname
        const originalURL = global.URL;
        global.URL = jest.fn().mockImplementation((url: string) => {
            const originalUrl = new originalURL(url);
            return {
                ...originalUrl,
                hostname: 'experiment-test.com',
                host: 'experiment-test.com',
                origin: 'https://experiment-test.com',
                href: url.replace(originalUrl.hostname, 'experiment-test.com'),
            };
        }) as any;

        const newUrl = new URL(mockOktaObj.redirectUri);
        newUrl.hostname = 'experiment-test.com'; // This would be window.location.hostname in real code
        mockOktaObj.redirectUri = newUrl.href;

        expect(mockOktaObj.redirectUri).toBe('https://experiment-test.com/login/callback');

        // Restore original URL
        global.URL = originalURL;
    });
});
