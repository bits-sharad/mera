import '@jobmatchingmodelpoc/shared-utils-cypress';

// The quick change to remove this linting error is to update tsconfig.base with a path
// that allows for something like "@ui/models/task". However, the cypress tests
// hung with that change. It needs more time to investigate.

import Task from '../models/task';
import {
    sampleTasks,
    tasksAfterUpdate,
    tasksAfterAdd,
    tasksAfterDelete,
    newTask,
    updateTask,
} from '../support/sampleTasks';
import {
    getTaskDeleteBtn,
    getTaskAddBtn,
    getTaskEditBtn,
    getTaskEditTitle,
    getTaskEditDesc,
    getTaskEditPriority,
    getTaskSaveBtn,
    getTaskItem,
} from '../support/task-management.po';

describe('Task management component', () => {
    const viewportWidth = 1200;
    const viewportHeight = 1500;
    beforeEach(() => {
        cy.intercept(
            {
                url: `**/*/${Cypress.env('API_NAME')}/v1/tasks`,
                method: 'GET',
            },
            { body: { tasks: sampleTasks } }
        ).as('getTasks');
        cy.visit('/tasks');
        cy.wait('@getTasks');
        cy.viewport(viewportWidth, viewportHeight);
    });

    it('renders the task delete button', () => {
        getTaskDeleteBtn().should('be.visible');
    });
});

const assertTaskDetailsAreRendered = () => {
    getTaskEditTitle().should('be.visible');
    getTaskEditDesc().should('be.visible');
    getTaskEditPriority().should('be.visible');
};

const typeNewTaskDetails = (task: Task) => {
    getTaskEditTitle().clear().type(task.name);
    getTaskEditDesc().clear().type(task.description);
    getTaskEditPriority().clear().type(task.priority.toString());
};

let isReact = false;

describe('Task management CRUD tests', () => {
    beforeEach(() => {
        cy.intercept(
            {
                url: `**/*/${Cypress.env('API_NAME')}/v1/tasks`,
                method: 'GET',
            },
            { body: { tasks: sampleTasks } }
        ).as('getTasks');
        cy.visit('/tasks');
        cy.get('[data-cy=title]').then(($title) => {
            if ($title.text().includes('MERN')) {
                isReact = true;
            }
        });
    });

    it('adds a new task and saves to the back end', () => {
        getTaskEditBtn().should('have.length', 3);

        getTaskAddBtn().click();

        assertTaskDetailsAreRendered();

        typeNewTaskDetails(newTask);

        cy.intercept(
            {
                url: `**/*/${Cypress.env('API_NAME')}/v1/tasks`,
                method: 'POST',
            },
            {
                statusCode: 201,
                headers: {
                    location: `/${Cypress.env('API_NAME')}/v1/tasks/${newTask.id}`,
                },
            }
        ).as('createTask');

        cy.intercept(
            {
                url: `**/*/${Cypress.env('API_NAME')}/v1/tasks`,
                method: 'GET',
            },
            { statusCode: 200, body: { tasks: tasksAfterAdd } }
        ).as('getTasks');

        getTaskSaveBtn().click();
        cy.wait('@createTask');

        if (isReact) {
            cy.wait('@getTasks'); // react
        }

        getTaskEditBtn().should('have.length', 4);

        getTaskItem().get('[data-cy=task-name]').last().contains(newTask.name);
        getTaskItem().get('[data-cy=task-desc]').last().contains(newTask.description);
        getTaskItem()
            .get('[data-cy=task-priority]')
            .last()
            .contains(`Priority: ${newTask.priority}`);
    });

    it('updates the new task', () => {
        if (!isReact) {
            getTaskEditBtn().should('have.length', 3);

            getTaskEditBtn().eq(2).click();

            assertTaskDetailsAreRendered();

            typeNewTaskDetails(updateTask);

            cy.intercept(
                {
                    url: `**/*/${Cypress.env('API_NAME')}/v1/tasks`,
                    method: 'POST',
                },
                { statusCode: 201 }
            ).as('updateTask');

            cy.intercept(
                {
                    url: `**/*/${Cypress.env('API_NAME')}/v1/tasks`,
                    method: 'GET',
                },
                { statusCode: 200, body: { tasks: tasksAfterUpdate } }
            ).as('getTasks');

            getTaskSaveBtn().click();

            if (isReact) {
                cy.wait('@getTasks'); // react
            }

            getTaskItem().get('[data-cy=task-name]').last().contains(updateTask.name);
            getTaskItem().get('[data-cy=task-desc]').last().contains(updateTask.description);
            getTaskItem()
                .get('[data-cy=task-priority]')
                .last()
                .contains(`Priority: ${updateTask.priority}`);

            getTaskEditBtn().should('have.length', 3);
        }
    });

    it('deletes the new/updated task', () => {
        getTaskEditBtn().should('have.length', 3);

        cy.intercept(
            {
                url: `**/*/${Cypress.env('API_NAME')}/v1/tasks/*`,
                method: 'DELETE',
            },
            { statusCode: 204 }
        ).as('deleteTask');
        cy.intercept(
            {
                url: `**/*/${Cypress.env('API_NAME')}/v1/tasks`,
                method: 'GET',
            },
            { statusCode: 200, body: { tasks: tasksAfterDelete } }
        ).as('getTasks');

        getTaskDeleteBtn().eq(2).click();

        cy.wait('@deleteTask');
        // Explicitly wait for the GET response after the POST to ensure that the tasks
        // have been rendered before making the assertions below
        cy.wait('@getTasks');

        getTaskDeleteBtn().should('have.length', 2);
    });
});
