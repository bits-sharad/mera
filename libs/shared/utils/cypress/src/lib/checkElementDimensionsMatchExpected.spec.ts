import 'cypress';
// eslint-disable-next-line import/no-extraneous-dependencies
import { expect as jestExpect } from '@jest/globals';
import { mock } from 'jest-mock-extended';

import checkElementDimensionsMatchExpected from './checkElementDimensionsMatchExpected';

/**
 * This function creates a mock JQuery object and a mock DOMRect object, sets the x, y, width, and height properties of the mock DOMRect object to the passed values, and sets
 * the getBoundingClientRect method of the mock HTMLElement object to return the mock DOMRect object. The mock JQuery object's get method is also set to return an array containing
 * the mock HTMLElement object.
 * @param {number} x - The x coordinate of the mock Jquery element.
 * @param {number} y - The y coordinate of the mock Jquery element.
 * @param {number} width - The width of the mock Jquery element.
 * @param {number} height - The height of the mock Jquery element.
 * @returns {object} - Returns a mocked JQuery object with the passed x, y, width and height as the element's bounding client rect values.
 */
function createMockJqueryElement(
    x: number,
    y: number,
    width: number,
    height: number
): JQuery<HTMLElement> {
    const mockJqueryElement = mock<JQuery<HTMLElement>>();
    const mockDOMRect = mock<DOMRect>();
    mockDOMRect.x = x;
    mockDOMRect.y = y;
    mockDOMRect.width = width;
    mockDOMRect.height = height;

    const mockElement = mock<HTMLElement>();
    mockElement.getBoundingClientRect.mockReturnValue(mockDOMRect);

    mockJqueryElement.get.mockReturnValue([mockElement]);
    return mockJqueryElement;
}

describe('checkElementDimensionsMatchExpected', () => {
    it('produces true for dimensions which match the expected values', () => {
        const mockJqueryElement = createMockJqueryElement(50, 70, 100, 200);

        const result = checkElementDimensionsMatchExpected(
            {
                xCoordinate: 50,
                yCoordinate: 70,
                width: 100,
                height: 200,
            },
            mockJqueryElement
        );

        jestExpect(result.x.success).toBeTruthy();
        jestExpect(result.y.success).toBeTruthy();
        jestExpect(result.width.success).toBeTruthy();
        jestExpect(result.height.success).toBeTruthy();
    });
});

describe('checkElementDimensionsMatchExpectedWithinErrorMargin', () => {
    it('produces true for dimensions which match within the error margin', () => {
        const mockJqueryElement = createMockJqueryElement(51, 69, 100.5, 199.01);

        const result = checkElementDimensionsMatchExpected(
            {
                xCoordinate: 50,
                yCoordinate: 70,
                width: 100,
                height: 200,
            },
            mockJqueryElement
        );

        jestExpect(result.x.success).toBeTruthy();
        jestExpect(result.y.success).toBeTruthy();
        jestExpect(result.width.success).toBeTruthy();
        jestExpect(result.height.success).toBeTruthy();
    });
});

describe('checkElementDimensionsDoNotMatchExpected', () => {
    it('produces false for dimensions which do match within the error margin', () => {
        const mockJqueryElement = createMockJqueryElement(51.01, 68.99, 101.5, 198.01);

        const result = checkElementDimensionsMatchExpected(
            {
                xCoordinate: 40,
                yCoordinate: 90,
                width: 140,
                height: 220,
            },
            mockJqueryElement
        );

        jestExpect(result.x.success).toBeFalsy();
        jestExpect(result.y.success).toBeFalsy();
        jestExpect(result.width.success).toBeFalsy();
        jestExpect(result.height.success).toBeFalsy();
    });
});
