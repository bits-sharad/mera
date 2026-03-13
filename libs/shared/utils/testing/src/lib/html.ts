/**
 * A helper function which queries the supplied HTML for the first element matching the supplied selector.
 * Throws an error (which can be used to fail the test) if a matching element cannot be found.
 * @param {HTMLElement} html - The HTML to search for the element in.
 * @param {string} selector  - The selector to use to locate the desired element (e.g. '.<class>', '#<id>', 'p').
 * @returns {HTMLElement} - The element, if found.
 */
export function queryForElement<HTMLSelectorType extends HTMLElement>(
    html: HTMLElement,
    selector: string
): HTMLSelectorType {
    const element: HTMLSelectorType | null = html.querySelector(selector);

    if (element === null) {
        throw new Error(`Could not find element '${selector}'.`);
    }

    return element;
}

/**
 * A helper function which queries the supplied HTML for elements matching the supplied class.
 * @param {HTMLElement} html - The HTML to search for the element in.
 * @param {string} className  - The class used to use to locate the desired elements.
 * @returns {Array<HTMLElement>} - An array of matching HTML elements.
 */
export function queryElementsByClassName(html: HTMLElement, className: string): Array<HTMLElement> {
    return Array.from(html.getElementsByClassName(className)) as Array<HTMLElement>;
}

/**
 * A helper function which checks if a HTML button element is enabled.
 * @param {HTMLButtonElement} button - The HTML button to be checked.
 * @returns {boolean} - If the button is enabled.
 */
export function isButtonEnabled(button: HTMLButtonElement): boolean {
    return !button.hasAttribute('disabled');
}
