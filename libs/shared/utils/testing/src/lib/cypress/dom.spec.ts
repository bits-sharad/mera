import { tryParseMeasurement } from './dom';

describe('colors', () => {
    describe('tryParseMeasurement', () => {
        it('parses a measurement value when supplied a suffix', () => {
            const input = '43px';

            const output = tryParseMeasurement(input, 'px');

            expect(output).toBe(43);
        });

        it('errors when the measurement does not include a suffix', () => {
            const input = '4';

            expect(() => tryParseMeasurement(input, 'px')).toThrow(
                "Invalid measurement '4' supplied for parsing."
            );
        });

        it('errors when the measurement does not include a value', () => {
            const input = 'rem';

            expect(() => tryParseMeasurement(input, 'rem')).toThrow(
                "Invalid measurement 'rem' supplied for parsing."
            );
        });

        it('errors when the measurement suffix does not match the supplied one', () => {
            const input = '40rem';

            expect(() => tryParseMeasurement(input, 'px')).toThrow(
                "Parsed suffix 'em' does not match expected suffix 'px'."
            );
        });

        it('errors when the parsed value is not a valid number', () => {
            const input = '4apx';

            expect(() => tryParseMeasurement(input, 'px')).toThrow(
                'Failed to parse measurement of element.'
            );
        });
    });
});
