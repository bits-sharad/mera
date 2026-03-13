import { assertElementDimensions } from './lib/commands';
import AssertElementDimensionsParams from './lib/models/assertElementDimensionsParams';

declare global {
    // eslint-disable-next-line @typescript-eslint/no-namespace
    namespace Cypress {
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        interface Chainable<Subject> {
            /**
             * Asserts that an element has expected dimensions.
             */
            assertElementDimensions(params: AssertElementDimensionsParams): void;
        }
    }
}

Cypress.Commands.add('assertElementDimensions', assertElementDimensions);
