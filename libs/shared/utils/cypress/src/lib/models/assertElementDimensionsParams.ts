import Dimensions from './dimensions';

interface AssertElementDimensionsParams {
    /**
     * A getter function which returns the element to be verified.
     */
    elementGetter: () => Cypress.Chainable<JQuery<HTMLElement>>;
    /**
     * The index of the element to get from the list. Omit if the element does not return a list.
     */
    index?: number;
    /**
     * The dimensions to be checked against. Supply values only for the dimensions required.
     */
    expectedDimensions: Dimensions;
}

export default AssertElementDimensionsParams;
