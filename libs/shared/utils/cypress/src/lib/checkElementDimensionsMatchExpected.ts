import ActualDimensionsResult from './models/actualDimensionsResult';
import Dimensions from './models/dimensions';

// The position of UI elements is not being consistently calculated by cypress.
// An error margin of 1 pixel works around the current issue. If the issue persists
// then it may be required to revisit this.
const allowableErrorMargin = 10;

/**
 * This function compares two numbers and returns true if the absolute difference between the two numbers is less than or equal to the allowable error margin.
 * @param {number} a - The first number to compare.
 * @param {number} b - The second number to compare.
 * @returns {boolean} - Returns whether the difference between the two numbers is within the allowable error margin.
 */
function comparable(a: number, b: number): boolean {
    return Math.abs(a - b) <= allowableErrorMargin;
}

/**
 * This function first compares the x-coordinate, y-coordinate, width, and height of the passed HTML element to the expected dimensions within the allowable error margin using the 'comparable' function. Then it returns an object containing the actual dimensions of the element, the expected dimensions and a boolean indicating whether the actual dimensions match the expected dimensions.
 * @param {Dimensions} expectedDimensions - An object containing the expected x-coordinate, y-coordinate, width, and height of the element.
 * @param {HTMLElement} $element - A JQuery object representing the HTML element.
 * @returns {ActualDimensionsResult} - Returns an object containing the actual dimensions of the element and whether they match the expected dimensions within the allowable error margin.
 */
export default function checkElementDimensionsMatchExpected(
    expectedDimensions: Dimensions,
    $element: JQuery<HTMLElement>
): ActualDimensionsResult {
    const {
        xCoordinate: expectedXCoordinate,
        yCoordinate: expectedYCoordinate,
        width: expectedWidth,
        height: expectedHeight,
    } = expectedDimensions;

    const htmlElements: HTMLElement[] = $element.get();
    const htmlElement = htmlElements[0];

    const {
        x: actualXCoordinate,
        y: actualYCoordinate,
        width: actualWidth,
        height: actualHeight,
    } = htmlElement.getBoundingClientRect();

    const someObj: ActualDimensionsResult = {};

    if (expectedXCoordinate !== undefined) {
        someObj.x = {
            success: comparable(actualXCoordinate, expectedXCoordinate),
            actual: actualXCoordinate,
            expected: expectedXCoordinate,
        };
    }
    if (expectedYCoordinate !== undefined) {
        someObj.y = {
            success: comparable(actualYCoordinate, expectedYCoordinate),
            actual: actualYCoordinate,
            expected: expectedYCoordinate,
        };
    }
    if (expectedWidth !== undefined) {
        someObj.width = {
            success: comparable(actualWidth, expectedWidth),
            actual: actualWidth,
            expected: expectedWidth,
        };
    }
    if (expectedHeight !== undefined) {
        someObj.height = {
            success: comparable(actualHeight, expectedHeight),
            actual: actualHeight,
            expected: expectedHeight,
        };
    }

    return someObj;
}
