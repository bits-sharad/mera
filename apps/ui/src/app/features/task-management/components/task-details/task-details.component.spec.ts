import { ComponentFixture, TestBed } from '@angular/core/testing';
import { FormsModule } from '@angular/forms';

import { queryForElement } from '@jobmatchingmodelpoc/shared-utils-testing';

import TaskDetailsComponent from './task-details.component';
import SharedModule from '../../../../shared/shared.module';
import Task from '../../models/task';

describe('TaskDetailsComponent', () => {
    let component: TaskDetailsComponent;
    let fixture: ComponentFixture<TaskDetailsComponent>;
    let compiled: HTMLElement;

    const expectedTask = new Task('abc123', 'name', 'description', 1, false);

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            declarations: [TaskDetailsComponent],
            imports: [FormsModule, SharedModule],
        }).compileComponents();
    });

    beforeEach(() => {
        fixture = TestBed.createComponent(TaskDetailsComponent);
        component = fixture.componentInstance;
        component.task = expectedTask;
        fixture.detectChanges();
        compiled = fixture.nativeElement as HTMLElement;
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('initializes the task to edit with the task input', () => {
        expect(component.taskToEdit).toEqual({
            id: 'abc123',
            name: 'name',
            description: 'description',
            priority: 1,
            isNew: false,
        });
    });

    it('emits the closed event', () => {
        const emitClosedSpy = jest.spyOn(component.closed, 'emit');
        const closeButton = queryForElement<HTMLButtonElement>(compiled, '.details__close button');
        closeButton.click();
        fixture.detectChanges();

        expect(emitClosedSpy).toHaveBeenCalledTimes(1);
    });

    it('triggers the saving of an edited task', () => {
        const emitSavedSpy = jest.spyOn(component.saved, 'emit');
        const saveButton = queryForElement<HTMLButtonElement>(compiled, '.details__save button');

        [
            {
                inputId: '#nameInput',
                newValue: 'edited task name',
            },
            {
                inputId: '#descriptionInput',
                newValue: 'edited task description',
            },
            {
                inputId: '#priorityInput',
                newValue: '5',
            },
        ].forEach(({ inputId, newValue }) => {
            // Update the value for the new task.
            const input = queryForElement<HTMLInputElement>(compiled, inputId);
            input.value = newValue;
            // Dispatch a DOM event so that Angular learns of input value change.
            input.dispatchEvent(new Event('input'));
        });
        fixture.detectChanges();

        saveButton.click();
        fixture.detectChanges();

        expect(emitSavedSpy).toHaveBeenCalledTimes(1);
        expect(emitSavedSpy).toHaveBeenCalledWith({
            id: 'abc123',
            name: 'edited task name',
            description: 'edited task description',
            priority: 5,
            isNew: false,
        });
    });
});
