import { getRGBString } from './colors';

describe('colors', () => {
    describe('getRGBString', () => {
        const testData = [
            {
                input: {
                    r: 10,
                    g: 50,
                    b: 100,
                },
                expectedOutput: 'rgb(10, 50, 100)',
            },
            {
                input: {
                    r: 0,
                    g: 0,
                    b: 0,
                },
                expectedOutput: 'rgb(0, 0, 0)',
            },
            {
                input: {
                    r: 255,
                    g: 255,
                    b: 255,
                },
                expectedOutput: 'rgb(255, 255, 255)',
            },
        ];

        testData.forEach(({ input, expectedOutput }) => {
            it('converts an RGB object to a string representation', () => {
                const output = getRGBString(input);

                expect(output).toEqual(expectedOutput);
            });
        });
    });
});
