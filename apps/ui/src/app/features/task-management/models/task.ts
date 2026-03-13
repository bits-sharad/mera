import { v4 as uuidv4 } from 'uuid';

export default class Task {
    id: string;

    name: string;

    description: string;

    priority: number;

    isNew: boolean;

    /**
     * @param {string} id - the id of the task
     * @param {string} name - the name of the task
     * @param {string} description - the description of the task
     * @param {number} priority - the priority of the task
     * @param {boolean} isNew - whether the task is new or not
     */
    constructor(id: string, name: string, description: string, priority: number, isNew: boolean) {
        this.id = id;
        this.name = name;
        this.description = description;
        this.priority = priority;
        this.isNew = isNew;
    }

    /**
     * Builds and returns a default Task object
     * @returns {Task} a new Task object with default values
     */
    static buildDefault(): Task {
        return new Task(uuidv4(), '', '', 0, true);
    }
}
