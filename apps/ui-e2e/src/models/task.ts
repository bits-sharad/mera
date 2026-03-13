import { v4 as uuidv4 } from 'uuid';

export default class Task {
    id: string;

    name: string;

    description: string;

    priority: number;

    isNew: boolean;

    /**
     * @param {string} id - The ID of the task.
     * @param {string} name - The name of the task.
     * @param {string} description - The description of the task.
     * @param {number} priority - The priority of the task.
     * @param {boolean} isNew - A flag indicating whether the task is new or not.
     */
    constructor(id: string, name: string, description: string, priority: number, isNew: boolean) {
        this.id = id;
        this.name = name;
        this.description = description;
        this.priority = priority;
        this.isNew = isNew;
    }

    /**
     * @returns {Task} - Returns a new task object with default values.
     */
    static buildDefault(): Task {
        return new Task(uuidv4(), '', '', 0, true);
    }
}
