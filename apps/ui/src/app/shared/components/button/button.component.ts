import { Component, Input, Output, EventEmitter, OnInit } from '@angular/core';

@Component({
    selector: 'polaris-button',
    templateUrl: './button.component.html',
    styleUrls: ['./button.component.scss'],
    standalone: false,
})
export default class ButtonComponent implements OnInit {
    @Input() label!: string;

    @Input() isDisabled = false;

    @Input() size = 'regular';

    @Input() theme = 'primary';

    @Output() clicked = new EventEmitter<void>();

    buttonSizeClass = '';

    buttonThemeClass = '';

    /**
     * Sets the size and theme classes for the component.
     */
    ngOnInit(): void {
        const buttonPrefix = 'btn--';
        this.buttonSizeClass = `${buttonPrefix}${this.size}`;
        this.buttonThemeClass = `${buttonPrefix}${this.theme}`;
    }

    /**
     * Emits an event if button is clicked.
     */
    onButtonClick() {
        this.clicked.emit();
    }
}
