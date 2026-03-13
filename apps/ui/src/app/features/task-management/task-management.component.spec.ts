/* eslint-disable max-classes-per-file */ // This is needed to support declaring multiple stubbed components.

import { Component, Output, EventEmitter, Input } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { FormsModule } from '@angular/forms';
import { of } from 'rxjs';

import { queryForElement } from '@jobmatchingmodelpoc/shared-utils-testing';

import Task from './models/task';
import TaskManagementService from './services/task-management.service';
import TaskManagementComponent from './task-management.component';
import TaskChangeEvent from './types/taskChangeEvent';

/**
 * Stub component for the Task List.
 */
@Component({
    selector: 'polaris-task-list',
    template: `<div>
        Task List Stub
        <div class="list__add-new">
            <button (click)="onAddClick()">Button</button>
        </div>
        <div class="list__delete"><button (click)="onDeleteClick()">Button</button></div>
        <div class="list__edit"><button (click)="onEditClick()">Button</button></div>
    </div>`,
})
class TaskListStubComponent {
    @Input() isDisabled!: boolean;

    @Input() tasks!: Array<Task>;

    @Output() addTask = new EventEmitter<void>();

    @Output() deleteTask = new EventEmitter<TaskChangeEvent>();

    @Output() editTask = new EventEmitter<TaskChangeEvent>();

    /**
     * Emits an event to add a new task
     */
    onAddClick() {
        this.addTask.emit();
    }

    /**
     * Emits an event to delete a task
     */
    onDeleteClick() {
        this.deleteTask.emit({ task: Task.buildDefault(), index: 0 });
    }

    /**
     * Emits an event to edit a task
     */
    onEditClick() {
        const taskToEdit = Task.buildDefault();
        taskToEdit.id = 'abc123 task to edit';
        this.editTask.emit({ task: taskToEdit, index: 1 });
    }
}

/**
 * Stub component for the Task Details.
 */
@Component({
    selector: 'polaris-task-details',
    template: `<div class="details">
        Task Details Stub
        <div class="details__close"><button (click)="onCloseClick()">Button</button></div>
        <div class="details__save-create">
            <button (click)="onSaveCreateClick()">Button</button>
        </div>
        <div class="details__save-edit"><button (click)="onSaveEditClick()">Button</button></div>
    </div>`,
})
class TaskDetailsStubComponent {
    @Input() task!: Task;

    @Output() closed = new EventEmitter<void>();

    @Output() saved = new EventEmitter<Task>();

    /**
     * Emits an event to close the task detail view
     */
    onCloseClick() {
        this.closed.emit();
    }

    /**
     * Emits an event to create a new task
     */
    onSaveCreateClick() {
        const taskToCreate = Task.buildDefault();
        taskToCreate.isNew = true;
        taskToCreate.name = 'abc123 new task to create';

        this.saved.emit(taskToCreate);
    }

    /**
     * Emits an event to edit an existing task
     */
    onSaveEditClick() {
        const taskToCreate = Task.buildDefault();
        taskToCreate.isNew = false;
        taskToCreate.name = 'abc123 existing task to edit';

        this.saved.emit(taskToCreate);
    }
}

describe('TaskManagementComponent', () => {
    let component: TaskManagementComponent;
    let fixture: ComponentFixture<TaskManagementComponent>;
    let compiled: HTMLElement;
    let taskManagementServiceStub: {
        getTask: jest.Mock;
        getTasks: jest.Mock;
        createTask: jest.Mock;
        deleteTask: jest.Mock;
        updateTask: jest.Mock;
    };
    let mockTasks: Array<Task>;

    beforeEach(() => {
        mockTasks = [
            new Task('abc', 'Mock Task Name 1', 'Mock Task Desc 1', 1, false),
            new Task('def', 'Mock Task Name 2', 'Mock Task Desc 2', 2, false),
            new Task('ghi', 'Mock Task Name 3', 'Mock Task Desc 3', 3, false),
        ];

        taskManagementServiceStub = {
            getTask: jest.fn(),
            getTasks: jest.fn().mockReturnValue(of({ tasks: [...mockTasks] })),
            createTask: jest.fn(),
            deleteTask: jest.fn(),
            updateTask: jest.fn(),
        };

        TestBed.configureTestingModule({
            declarations: [TaskManagementComponent],
            imports: [FormsModule, TaskDetailsStubComponent, TaskListStubComponent],
            providers: [
                {
                    provide: TaskManagementService,
                    useValue: taskManagementServiceStub,
                },
            ],
        });
    });

    beforeEach(async () => {
        await TestBed.compileComponents();
        fixture = TestBed.createComponent(TaskManagementComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
        compiled = fixture.nativeElement as HTMLElement;
    });

    it('should create the component', () => {
        expect(component).toBeTruthy();
    });

    it('does not start in edit mode', () => {
        expect(() => queryForElement<HTMLDivElement>(compiled, '.details')).toThrow(
            "Could not find element '.details'."
        );
        expect(component.isEditMode).toBeFalsy();
    });

    it('edits a task', () => {
        const editTaskSpy = jest.spyOn(component, 'editTask');

        const editTaskButton = queryForElement<HTMLButtonElement>(compiled, '.list__edit button');
        editTaskButton.click();
        fixture.detectChanges();

        expect(editTaskSpy).toHaveBeenCalledTimes(1);
        expect(component.taskToEdit.id).toBe('abc123 task to edit');
        expect(component.isEditMode).toBeTruthy();
    });

    it('deletes a task', () => {
        taskManagementServiceStub.deleteTask.mockReturnValue(of({}));

        const deleteTaskButton = queryForElement<HTMLButtonElement>(
            compiled,
            '.list__delete button'
        );

        expect(component.tasks[0].id).toBe('abc');
        expect(taskManagementServiceStub.getTasks).toHaveBeenCalledTimes(1);

        deleteTaskButton.click();
        fixture.detectChanges();

        expect(taskManagementServiceStub.deleteTask).toHaveBeenCalledTimes(1);
        expect(taskManagementServiceStub.deleteTask).toHaveBeenCalledWith('abc');
        expect(taskManagementServiceStub.getTasks).toHaveBeenCalledTimes(2);
    });
});
