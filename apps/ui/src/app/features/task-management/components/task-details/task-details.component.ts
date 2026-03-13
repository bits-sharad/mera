import { Component, Input, Output, EventEmitter, OnInit } from '@angular/core';

import Task from '../../models/task';

@Component({
    selector: 'polaris-task-details',
    templateUrl: './task-details.component.html',
    styleUrls: ['./task-details.component.scss'],
    standalone: false,
})
export default class TaskDetailsComponent implements OnInit {
    @Input() task!: Task;

    @Output() closed = new EventEmitter<void>();

    @Output() saved = new EventEmitter<Task>();

    /**
     * A local Task model which can be updated within the details component.
     * This avoids mutating the original Task passed in from the parent.
     */
    taskToEdit: Task = Task.buildDefault();

    /**
     * Initializes the component by copying the properties of the task to be edited to a new object
     * for editing
     */
    ngOnInit() {
        this.taskToEdit.id = this.task.id;
        this.taskToEdit.name = this.task.name;
        this.taskToEdit.priority = this.task.priority;
        this.taskToEdit.description = this.task.description;
        this.taskToEdit.isNew = this.task.isNew;
    }

    /**
     * Emits a closed event when the close button is clicked
     */
    onCloseClick() {
        this.closed.emit();
    }

    /**
     * Emits a saved event with the edited task object when the save button is clicked
     */
    onSaveClick() {
        this.saved.emit(this.taskToEdit);
    }
}
