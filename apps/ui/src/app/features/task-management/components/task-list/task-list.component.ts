import { Component, Input, Output, EventEmitter } from '@angular/core';

import Task from '../../models/task';
import TaskChangeEvent from '../../types/taskChangeEvent';

@Component({
    selector: 'polaris-task-list',
    templateUrl: './task-list.component.html',
    styleUrls: ['./task-list.component.scss'],
    standalone: false,
})
export default class TaskListComponent {
    @Input() tasks!: Array<Task>;

    @Input() isDisabled = false;

    @Output() addTask = new EventEmitter<void>();

    @Output() editTask = new EventEmitter<TaskChangeEvent>();

    @Output() deleteTask = new EventEmitter<TaskChangeEvent>();

    /**
     * Emits an addTask event when the "Add Task" button is clicked
     */
    onTaskAddClick() {
        this.addTask.emit();
    }

    /**
     * Emits an editTask event with the task object and its index when the "Edit" button is clicked from the task component
     * @param {Task} task - The task object that needs to be edited
     * @param {number} index - The index of the task object in the list
     */
    onTaskEditClick(task: Task, index: number) {
        this.editTask.emit({
            task,
            index,
        });
    }

    /**
     * Emits a deleteTask event with the task object and its index when the "Delete" button is clicked for a task
     * @param {Task} task - The task object that needs to be deleted
     * @param {number} index - The index of the task object in the list
     */
    onTaskDeleteClick(task: Task, index: number) {
        this.deleteTask.emit({
            task,
            index,
        });
    }

    // eslint-disable-next-line class-methods-use-this
    taskTrackBy = (_: number, task: Task) => task.id;
}
