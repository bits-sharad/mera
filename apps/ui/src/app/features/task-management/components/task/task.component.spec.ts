import { ComponentFixture, TestBed } from '@angular/core/testing';
import { RouterTestingModule } from '@angular/router/testing';

import TaskComponent from './task.component';
import SharedModule from '../../../../shared/shared.module';
import Task from '../../models/task';

describe('TaskComponent', () => {
    let component: TaskComponent;
    let fixture: ComponentFixture<TaskComponent>;

    const expectedTask = new Task('abc123', 'name', 'description', 1, false);

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [SharedModule, RouterTestingModule],
            declarations: [TaskComponent],
        }).compileComponents();
    });

    beforeEach(() => {
        fixture = TestBed.createComponent(TaskComponent);
        component = fixture.componentInstance;
        component.task = expectedTask;

        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });
});
