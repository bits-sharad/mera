import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { fakeAsync, TestBed, tick } from '@angular/core/testing';
import { v4 as uuidv4 } from 'uuid';

import TaskManagementService from './task-management.service';
import Task from '../models/task';

const API_NAME = 'api';
const API_PORT = '8080';

describe('TaskManagementService', () => {
    const apiBaseUrl = `http://localhost:${API_PORT}/${API_NAME}/v1`;
    let service: TaskManagementService;
    let httpTestingController: HttpTestingController;

    beforeEach(() => {
        TestBed.configureTestingModule({
            imports: [HttpClientTestingModule],
            providers: [TaskManagementService],
        });

        httpTestingController = TestBed.inject(HttpTestingController);
        service = TestBed.inject(TaskManagementService);
    });

    afterEach(() => {
        // After every test, assert that there are no more pending requests.
        httpTestingController.verify();
    });

    it('should create the service', () => {
        expect(service).toBeTruthy();
    });

    it('performs a HTTP Get with the correct URL when getTask is invoked', fakeAsync(() => {
        // Arrange
        const testResponseData = {
            name: 'Test Task Name',
            description: 'Test Task Desc',
            priority: 1,
            id: '1234567890ABCDEFab000001',
        };
        const testTaskId = uuidv4();

        // Act
        service.getTask(testTaskId).subscribe((responseData) =>
            // When the observable resolves, the result should match the test data.
            expect(responseData).toEqual(testResponseData)
        );

        // Assert
        // Verify the correct URL has been used with the correct HTTP method.
        const req = httpTestingController.expectOne(`${apiBaseUrl}/tasks/${testTaskId}`);
        expect(req.request.method).toBe('GET');

        // Respond with mock data, causing Observable to resolve.
        // Subscribe callback asserts that the correct data was returned.
        req.flush(testResponseData);
        tick();
    }));

    it('performs a HTTP Get with the correct URL when getTasks is invoked', fakeAsync(() => {
        // Arrange
        const testResponseData = [
            {
                name: 'Test Task Name 1',
                description: 'Test Task Desc 1',
                priority: 1,
                id: '1234567890ABCDEFab000001',
            },
            {
                name: 'Test Task Name 2',
                description: 'Test Task Desc 2',
                priority: 1,
                id: '1234567890ABCDEFab000001',
            },
        ];

        // Act
        service.getTasks().subscribe((responseData) =>
            // When the observable resolves, the result should match the test data.
            expect(responseData).toEqual(testResponseData)
        );

        // Assert
        // Verify the correct URL has been used with the correct HTTP method.
        const req = httpTestingController.expectOne(`${apiBaseUrl}/tasks`);
        expect(req.request.method).toBe('GET');

        // Respond with mock data, causing Observable to resolve.
        // Subscribe callback asserts that correct data was returned.
        req.flush(testResponseData);
        tick();
    }));

    it('performs a HTTP Post with the correct URL and body when createTask is invoked', fakeAsync(() => {
        // Arrange
        const testResponseData = '';
        const testTaskId = uuidv4();
        const testTaskName = 'Test Task Name';
        const testTaskDesc = 'Test Task Desc.';
        const testTaskPriority = 4;
        const testTask: Task = new Task(
            testTaskId,
            testTaskName,
            testTaskDesc,
            testTaskPriority,
            true
        );
        const testTaskRequestBody = {
            name: testTaskName,
            description: testTaskDesc,
            priority: testTaskPriority,
        };

        // Act
        service.createTask(testTask).subscribe((responseData) => {
            // When the observable resolves, the result should match the test data.
            expect(responseData.body).toEqual(testResponseData);
        });

        // Assert
        // Verify the correct URL has been used with the correct HTTP method.
        const req = httpTestingController.expectOne(`${apiBaseUrl}/tasks`);
        expect(req.request.method).toBe('POST');
        expect(req.request.body).toEqual(testTaskRequestBody);

        // Respond with mock data, causing Observable to resolve.
        // Subscribe callback asserts that correct data was returned.
        req.flush(testResponseData);
        tick();
    }));

    it('performs a HTTP Delete with the correct URL when deleteTask is invoked', fakeAsync(() => {
        // Arrange
        const testResponseData = null;
        const testTaskId = uuidv4();

        // Act
        service.deleteTask(testTaskId).subscribe((responseData) =>
            // When the observable resolves, the result should match the test data.
            expect(responseData).toEqual(testResponseData)
        );

        // Assert
        // Verify the correct URL has been used with the correct HTTP method.
        const req = httpTestingController.expectOne(`${apiBaseUrl}/tasks/${testTaskId}`);
        expect(req.request.method).toBe('DELETE');

        // Respond with mock data, causing Observable to resolve.
        // Subscribe callback asserts that correct data was returned.
        req.flush(testResponseData);
        tick();
    }));

    it('performs a HTTP Put with the correct URL and body when updateTask is invoked', fakeAsync(() => {
        // Arrange
        const testResponseData = null;
        const testTaskId = uuidv4();
        const testTaskName = 'Test Task Name';
        const testTaskDesc = 'Test Task Desc.';
        const testTaskPriority = 4;
        const testTask: Task = new Task(
            testTaskId,
            testTaskName,
            testTaskDesc,
            testTaskPriority,
            false
        );
        const testTaskRequestBody = {
            id: testTaskId,
            name: testTaskName,
            description: testTaskDesc,
            priority: testTaskPriority,
        };

        // Act
        service.updateTask(testTask).subscribe((responseData) =>
            // When the observable resolves, the result should match the test data.
            expect(responseData).toEqual(testResponseData)
        );

        // Assert
        // Verify the correct URL has been used with the correct HTTP method and request body.
        const req = httpTestingController.expectOne(`${apiBaseUrl}/tasks/${testTaskId}`);
        expect(req.request.method).toBe('PUT');
        expect(req.request.body).toEqual(testTaskRequestBody);

        // Respond with mock data, causing Observable to resolve.
        // Subscribe callback asserts that correct data was returned.
        req.flush(testResponseData);
        tick();
    }));
});
