/* eslint-disable import/prefer-default-export */

/**
 * Attempts to parse a measurement (width or height) number from its string representation
 * by removing its suffix.
 * @param {string} measurement - The measurement to be parsed. E.g. "40px".
 * @param {string} [suffix] - The suffix used in the measurement. E.g. "px". Defaults to "px".
 * @returns {number} - The parsed measurement number.
 * @throws - An error if parsing did not succeed.
 */
export const tryParseMeasurement = (measurement: string, suffix = 'px'): number => {
    if (measurement.length <= suffix.length) {
        throw new Error(`Invalid measurement '${measurement}' supplied for parsing.`);
    }

    const parsedSuffix = measurement.substring(
        measurement.length - suffix.length,
        measurement.length
    );
    if (parsedSuffix !== suffix) {
        throw new Error(
            `Parsed suffix '${parsedSuffix}' does not match expected suffix '${suffix}'.'`
        );
    }

    const withoutSuffix = measurement.substring(0, measurement.length - suffix.length);
    const parsedMeasurement = Number(withoutSuffix);

    if (Number.isNaN(parsedMeasurement)) {
        throw new Error('Failed to parse measurement of element.');
    }

    return parsedMeasurement;
};
