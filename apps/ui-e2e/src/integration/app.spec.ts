import { getRGBString, getFullRGBString } from '@jobmatchingmodelpoc/shared-utils-testing';
import '@jobmatchingmodelpoc/shared-utils-cypress';

import {
    getFooter,
    getHeader,
    getMain,
    getTitle,
    getCopyright,
    getVersion,
    getNavLinks,
    getLogo,
} from '../support/app.po';
import { sampleTasks } from '../support/sampleTasks';

const branding = {
    colors: {
        primaryContrast: getFullRGBString({
            r: 0,
            g: 0,
            b: 0,
            a: 0,
        }),
        primary: getRGBString({
            r: 240,
            g: 240,
            b: 240,
        }),
        secondary: getRGBString({
            r: 0,
            g: 0,
            b: 0,
        }),
    },
    fonts: {
        primary: 'Noto-Sans',
    },
};

describe('starter-app', () => {
    beforeEach(() => {
        cy.intercept(
            {
                url: `**/*/${Cypress.env('API_NAME')}/v1/tasks`,
                method: 'GET',
            },
            { body: { tasks: sampleTasks } }
        ).as('getTasks');
        cy.visit('/');
    });

    it('displays the application title', () => {
        getTitle().contains('Getting Started');
    });

    it('uses background colors adhering to branding', () => {
        getHeader().should('have.css', 'background-color', branding.colors.primaryContrast);
        getMain().should('have.css', 'background-color', branding.colors.primary);
        getFooter().should('have.css', 'background-color', branding.colors.secondary);
    });

    it('uses a font family adhering to branding', () => {
        // Verify the layout elements have the font-family set.
        getHeader().should('have.css', 'font-family', branding.fonts.primary);
        getMain().should('have.css', 'font-family', branding.fonts.primary);
        getFooter().should('have.css', 'font-family', branding.fonts.primary);

        // Verify individual text elements have the font-family set.
        getTitle().should('have.css', 'font-family', '"MMC Display-Condensed-Bold"');
        getCopyright().should('have.css', 'font-family', branding.fonts.primary);
        getVersion().should('have.css', 'font-family', branding.fonts.primary);
        getNavLinks().each((navLink) => {
            cy.wrap(navLink).should('have.css', 'font-family', branding.fonts.primary);
        });
    });

    it('displays the logo', () => {
        getLogo()
            .should('be.visible')
            .should('have.attr', 'src')
            .and('match', /mmc-logo.svg/);
    });

    it('should able to navigate to tasks when user clicks on tasklist', () => {
        cy.get('[data-cy=task-list]').click();
        cy.get('[data-cy=task-management]').should('be.visible');
    });
});
