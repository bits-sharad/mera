import { Component, Input, Output, EventEmitter } from '@angular/core';

import Task from '../../models/task';

@Component({
    selector: 'polaris-task',
    templateUrl: './task.component.html',
    styleUrls: ['./task.component.scss'],
    standalone: false,
})
export default class TaskComponent {
    @Input() task!: Task;

    @Input() isDisabled = false;

    @Output() edit = new EventEmitter<void>();

    @Output() delete = new EventEmitter<void>();

    /**
     * Emits an edit event when the "Edit" button is clicked
     */
    onEditClick() {
        this.edit.emit();
    }

    /**
     * Emits a delete event when the "Delete" button is clicked
     */
    onDeleteClick() {
        this.delete.emit();
    }
}
