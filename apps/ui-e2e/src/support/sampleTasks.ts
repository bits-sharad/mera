const baseTasks = [
    {
        id: '1234567890ABCDEFab000001',
        name: 'Renew TV license',
        description:
            'Curabitur fermentum odio in libero iaculis, eu pharetra lectus consectetur. Proin porta gravida mauris, sit amet fermentum ex ullamcorper eleifend. Duis risus nunc, rhoncus vitae elit sollicitudin, aliquet interdum tortor. Nulla consectetur lectus eu nulla mattis.',
        priority: 1,
    },
    {
        id: '1234567890ABCDEFab000002',
        name: 'Go for a run',
        desciption:
            'Integer hendrerit quam et purus ornare, ut efficitur nibh eleifend. Quisque turpis tellus, pulvinar ut nibh id, suscipit viverra nisi. Nulla pretium semper mi sit amet malesuada.',
        priority: 2,
    },
    {
        id: '1234567890ABCDEFab000003',
        name: 'Take the garbage out',
        description:
            'Aenean euismod hendrerit rutrum. Curabitur maximus sed ante finibus porttitor. Morbi et gravida elit. Orci varius natoque penatibus et magnis dis parturient montes, nascetur ridiculus mus.',
        priority: 4,
    },
];

/**
 * Performs shallow cloning of  tasks object
 * @returns {typeof baseTasks} Deep copies the task object, and returns new instance of tasks
 */
function getBaseTasksCopy() {
    return baseTasks.map((task) => ({ ...task }));
}

export const newTask = {
    id: '42',
    name: 'New E2E Test',
    description: 'Test to verify adding a new task',
    priority: 1000,
    isNew: true,
};
export const updateTask = {
    id: '1234567890ABCDEFab000003',
    name: 'Update E2E Test',
    description: 'Test to verify updating a task',
    priority: 1000,
    isNew: false,
};

const baseTasksWithNewTask = getBaseTasksCopy();
baseTasksWithNewTask.push({ ...newTask });

const baseTasksWithUpdatedTask = getBaseTasksCopy();
baseTasksWithUpdatedTask[2] = { ...updateTask };

const baseTasksWithDeletedTask = getBaseTasksCopy();
baseTasksWithDeletedTask.pop();

export const sampleTasks = getBaseTasksCopy();
export const tasksAfterAdd = baseTasksWithNewTask;
export const tasksAfterUpdate = baseTasksWithUpdatedTask;
export const tasksAfterDelete = baseTasksWithDeletedTask;
