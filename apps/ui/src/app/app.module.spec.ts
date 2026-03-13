import { OktaAuth } from '@okta/okta-auth-js';

import AppModule from './app.module';

jest.mock('@okta/okta-auth-js', () => ({
    OktaAuth: jest.fn().mockImplementation(() => ({
        tokenManager: { on: jest.fn() },
    })),
    default: jest.fn().mockImplementation(() => ({
        tokenManager: { on: jest.fn() },
    })),
}));

jest.mock('../environments/environment', () => ({
    default: {
        oktaConfig: 'value',
    },
}));

describe('AppModule', () => {
    it('creates okta instance using environment config values', () => {
        const app = new AppModule();
        expect(app).toBeTruthy();
        expect(OktaAuth).toHaveBeenCalledTimes(1);
        expect(OktaAuth).toHaveBeenCalledWith('value');
    });
});
