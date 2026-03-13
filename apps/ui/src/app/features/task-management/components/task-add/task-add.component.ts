import { Component, OnDestroy, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { Observable, Subscription } from 'rxjs';

import Task from '../../models/task';
import TaskManagementService from '../../services/task-management.service';

@Component({
    selector: 'polaris-task-add',
    templateUrl: './task-add.component.html',
    styleUrls: ['./task-add.component.scss'],
    standalone: false,
})
export default class TaskAddComponent implements OnInit, OnDestroy {
    /**
     * A local Task model which can be updated within the details component.
     * This avoids mutating the original Task passed in from the parent.
     */
    task: Task = Task.buildDefault();

    state$: Observable<object> | undefined;

    private getTaskSubscription!: Subscription;

    private saveTaskSubscription!: Subscription;

    /**
     * @param {TaskManagementService} service - An instance of Task Management service
     * @param {ActivatedRoute} route - Provides access to information about a route associated with a component that is loaded in an outlet
     * @param {Router} router - A service that provides navigation among views and URL manipulation capabilities
     */
    constructor(
        private service: TaskManagementService,
        private route: ActivatedRoute,
        private router: Router
    ) {}

    /**
     * Get Task Details for Editing
     */
    ngOnInit() {
        const id = this.route.snapshot.paramMap.get('id');
        if (id) {
            this.getTaskSubscription = this.service.getTask(id).subscribe((data) => {
                this.task = data;
                this.task.id = id;
            });
        }
    }

    /**
     * SaveDetails - saves a task to the service and refreshes the component's task list.
     */
    saveDetails() {
        const saveTask = this.task.isNew
            ? this.service.createTask(this.task)
            : this.service.updateTask(this.task);

        this.saveTaskSubscription = saveTask.subscribe(() => {
            this.router.navigateByUrl('/tasks');
        });
    }

    /**
     *
     */
    closeDetails() {
        this.router.navigateByUrl('/tasks');
    }

    /**
     * A callback method that performs custom clean-up, invoked immediately before a directive, pipe, or service instance is destroyed
     */
    ngOnDestroy() {
        if (this.getTaskSubscription) {
            this.getTaskSubscription.unsubscribe();
        }
        if (this.saveTaskSubscription) {
            this.saveTaskSubscription.unsubscribe();
        }
    }
}
