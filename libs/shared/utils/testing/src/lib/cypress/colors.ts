/**
 * Converts an RGB object into a string representation - 'rgb(x, y, z)'.
 * @param {object} params - Root object with all properties for RGB
 * @param {number} params.r - Red value in RGB.
 * @param {number} params.g - Green value in RGB.
 * @param {number} params.b - Blue value in RGB.
 * @returns {string} - A string representation of an RGB colour.
 */
export const getRGBString = ({ r, g, b }: { r: number; g: number; b: number }) =>
    `rgb(${r}, ${g}, ${b})`;

export const getFullRGBString = ({ r, g, b, a }: { r: number; g: number; b: number; a: number }) =>
    `rgba(${r}, ${g}, ${b}, ${a})`;
