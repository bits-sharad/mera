import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import environment from '../../../../environments/environment';
import Task from '../models/task';

interface TasksResult {
    tasks: Array<Task>;
}

@Injectable()
/** A class for managing the interaction with the Tasks API. */
export default class TaskManagementService {
    private tasksEndpointUrl = `${environment.apiBaseUrl}/tasks`;

    /**
     * Create a Task Management Service.
     * @param {HttpClient} http - The HTTP client to be used for all API calls.
     */
    constructor(private http: HttpClient) {}

    /**
     * Retrieve the task with the given ID.
     * @param {string} taskId - The ID of the task to retrieve.
     * @returns {Observable<Task>} - The retrieved task wrapped in an Observable.
     */
    getTask(taskId: string): Observable<Task> {
        return this.http.get<Task>(`${this.tasksEndpointUrl}/${taskId}`);
    }

    /**
     * Retrieve all tasks.
     * @returns {Observable<TasksResult>} - A collection containing all tasks, wrapped in an Observable.
     */
    getTasks(): Observable<TasksResult> {
        return this.http.get<TasksResult>(this.tasksEndpointUrl);
    }

    /**
     * Create the provided task.
     * @param {Task} task - The task to be created.
     * @returns {Observable<TasksResult>} - An HTTP response with an empty body wrapped in an Observable.
     * The entire HTTP response is returned so that the Location header containing
     * the ID of the newly created Task can be parsed.
     */
    createTask(task: Task) {
        const newTask = { name: task.name, description: task.description, priority: task.priority };
        return this.http.post(this.tasksEndpointUrl, newTask, { observe: 'response' });
    }

    /**
     * Delete the task with the given ID.
     * @param {string} taskId - The ID of the task to delete.
     * @returns {Observable} - An empty response body wrapped in an Observable.
     */
    deleteTask(taskId: string) {
        return this.http.delete(`${this.tasksEndpointUrl}/${taskId}`);
    }

    /**
     * Update the provided task.
     * @param {Task} task - The new version of the task to be updated.
     * @returns {Observable} - An empty response body wrapped in an Observable.
     */
    updateTask(task: Task) {
        const updatedTask = {
            id: task.id,
            name: task.name,
            description: task.description,
            priority: task.priority,
        };
        return this.http.put(`${this.tasksEndpointUrl}/${updatedTask.id}`, updatedTask);
    }
}
