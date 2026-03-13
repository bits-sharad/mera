import { HttpClientModule } from '@angular/common/http';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { RouterTestingModule } from '@angular/router/testing';
import { MockProxy, mock } from 'jest-mock-extended';
import { of } from 'rxjs';

import TaskAddComponent from './task-add.component';
import TaskManagementService from '../../services/task-management.service';

describe('TaskAddComponent', () => {
    let component: TaskAddComponent;
    let fixture: ComponentFixture<TaskAddComponent>;
    let mockActivatedRoute: {
        snapshot: {
            paramMap: {
                get: jest.Mock;
            };
        };
    };
    let mockRouter: MockProxy<Router>;
    let mockTaskService: {
        getTask: jest.Mock;
        getTasks: jest.Mock;
        createTask: jest.Mock;
        deleteTask: jest.Mock;
        updateTask: jest.Mock;
    };

    beforeEach(async () => {
        mockActivatedRoute = {
            snapshot: {
                paramMap: {
                    get: jest.fn(),
                },
            },
        };

        mockRouter = mock<Router>();

        mockTaskService = {
            getTask: jest.fn(),
            getTasks: jest.fn(),
            createTask: jest.fn(),
            deleteTask: jest.fn(),
            updateTask: jest.fn(),
        };

        await TestBed.configureTestingModule({
            imports: [FormsModule, HttpClientModule, RouterModule, RouterTestingModule],
            declarations: [TaskAddComponent],
            providers: [
                { provide: ActivatedRoute, useValue: mockActivatedRoute },
                { provide: Router, useValue: mockRouter },
                { provide: TaskManagementService, useValue: mockTaskService },
            ],
        }).compileComponents();

        fixture = TestBed.createComponent(TaskAddComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should get task details for editing', () => {
        const mockTask = {
            id: '1',
            name: 'Task 1',
            description: 'Task description',
            priority: 1,
            isNew: false,
        };

        mockActivatedRoute.snapshot.paramMap.get.mockReturnValue(mockTask.id);
        mockTaskService.getTask.mockReturnValue(of(mockTask));

        component.ngOnInit();

        expect(mockActivatedRoute.snapshot.paramMap.get).toHaveBeenCalledWith('id');
        expect(mockTaskService.getTask).toHaveBeenCalledWith(mockTask.id);
        expect(component.task).toEqual(mockTask);
    });

    it('should create a new task and navigate to /tasks', () => {
        const mockTask = {
            id: '1',
            name: 'Task 1',
            description: 'Task description',
            priority: 1,
            isNew: true,
        };

        component.task = mockTask;

        mockTaskService.createTask.mockReturnValue(of(null));

        component.saveDetails();

        expect(mockTaskService.createTask).toHaveBeenCalledWith(mockTask);
        expect(mockRouter.navigateByUrl).toHaveBeenCalledWith('/tasks');
    });

    it('should update an existing task and navigate to /tasks', () => {
        const mockTask = {
            id: '1',
            name: 'Task 1',
            description: 'Task description',
            priority: 1,
            isNew: false,
        };

        component.task = mockTask;

        mockTaskService.updateTask.mockReturnValue(of(null));

        component.saveDetails();

        expect(mockTaskService.updateTask).toHaveBeenCalledWith(mockTask);
        expect(mockRouter.navigateByUrl).toHaveBeenCalledWith('/tasks');
    });

    it('should navigate to /tasks', () => {
        component.closeDetails();

        expect(mockRouter.navigateByUrl).toHaveBeenCalledWith('/tasks');
    });
});
