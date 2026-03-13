/* eslint-disable jest/valid-expect */
import checkElementDimensionsMatchExpected from './checkElementDimensionsMatchExpected';
import ActualDimensionsResult from './models/actualDimensionsResult';
import AssertElementDimensionsParams from './models/assertElementDimensionsParams';

// eslint-disable-next-line import/prefer-default-export
export const assertElementDimensions = ({
    elementGetter,
    index = 0,
    expectedDimensions,
}: AssertElementDimensionsParams) => {
    elementGetter()
        .eq(index)
        .then(($element: JQuery<HTMLElement>) => {
            const {
                xCoordinate: expectedXCoordinate,
                yCoordinate: expectedYCoordinate,
                width: expectedWidth,
                height: expectedHeight,
            } = expectedDimensions;

            const { x, y, width, height }: ActualDimensionsResult =
                checkElementDimensionsMatchExpected(expectedDimensions, $element);

            if (expectedXCoordinate !== undefined) {
                expect(x?.success).to.equal(
                    true,
                    `x: expected ${x?.expected} to equal ${x?.actual}`
                );
            }
            if (expectedYCoordinate !== undefined) {
                expect(y?.success).to.equal(
                    true,
                    `y: expected ${y?.expected} to equal ${y?.actual}`
                );
            }
            if (expectedWidth !== undefined) {
                expect(width?.success).to.equal(
                    true,
                    `width: expected ${width?.expected} to equal ${width?.actual}`
                );
            }
            if (expectedHeight !== undefined) {
                expect(height?.success).to.equal(
                    true,
                    `height: expected ${height?.expected} to equal ${height?.actual}`
                );
            }
        });
};
