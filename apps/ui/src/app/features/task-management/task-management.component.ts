import { Component, OnDestroy, OnInit } from '@angular/core';
import { Subscription } from 'rxjs';

import Task from './models/task';
import TaskManagementService from './services/task-management.service';
import TaskChangeEvent from './types/taskChangeEvent';

@Component({
    selector: 'polaris-task-management',
    templateUrl: './task-management.component.html',
    styleUrls: ['./task-management.component.scss'],
    standalone: false,
})
export default class TaskManagementComponent implements OnInit, OnDestroy {
    /**
     * @param {TaskManagementService} service - An instance of Task Management service
     */
    constructor(private service: TaskManagementService) {}

    tasks: Array<Task> = [];

    isEditMode = false;

    taskToEdit: Task = Task.buildDefault();

    private getTaskSubscription!: Subscription;

    private createTaskSubscription!: Subscription;

    private updateTaskSubscription!: Subscription;

    private deleteTaskSubscription!: Subscription;

    /**
     * Retrieves a list of tasks from the service and updates the component's task list.
     */
    refreshTaskList() {
        this.getTaskSubscription = this.service.getTasks().subscribe((taskResponse) => {
            this.tasks = taskResponse.tasks;
        });
    }

    /**
     * Sets the component's edit mode flag to true and sets the task to edit to a default task object.
     */
    addNewTask() {
        this.isEditMode = true;
        this.taskToEdit = Task.buildDefault();
    }

    /**
     * deleteTask - deletes a task from the service and refreshes the component's task list.
     * @param {TaskChangeEvent} {index} - An object containing the index of the task to delete.
     */
    deleteTask({ index }: TaskChangeEvent) {
        const taskToDelete = this.tasks[index];
        this.deleteTaskSubscription = this.service
            .deleteTask(taskToDelete.id)
            .subscribe(() => this.refreshTaskList());
    }

    /**
     * editTask - sets the component's task to edit and sets the edit mode flag to true.
     * @param {TaskChangeEvent} {task} - An object containing the task to edit.
     */
    editTask({ task }: TaskChangeEvent) {
        this.taskToEdit = new Task(task.id, task.name, task.description, task.priority, false);
        this.isEditMode = true;
    }

    /**
     * Sets the component's edit mode flag to false.
     */
    closeDetails() {
        this.isEditMode = false;
    }

    /**
     * SaveDetails - saves a task to the service and refreshes the component's task list.
     * @param {Task} taskToSave - the task to save
     */
    saveDetails(taskToSave: Task) {
        if (taskToSave.isNew) {
            this.createTaskSubscription = this.service.createTask(taskToSave).subscribe(() => {
                this.refreshTaskList();
            });
        } else {
            this.updateTaskSubscription = this.service
                .updateTask(taskToSave)
                .subscribe(() => this.refreshTaskList());
        }

        this.closeDetails();
    }

    /**
     * Retrieves a list of tasks from the service on initialization of the component.
     */
    ngOnInit() {
        this.refreshTaskList();
    }

    /**
     * A callback method that performs custom clean-up, invoked immediately before a directive, pipe, or service instance is destroyed
     */
    ngOnDestroy() {
        if (this.getTaskSubscription) {
            this.getTaskSubscription.unsubscribe();
        }
        if (this.createTaskSubscription) {
            this.createTaskSubscription.unsubscribe();
        }
        if (this.updateTaskSubscription) {
            this.updateTaskSubscription.unsubscribe();
        }
        if (this.deleteTaskSubscription) {
            this.deleteTaskSubscription.unsubscribe();
        }
    }
}
