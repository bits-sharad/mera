import Task from '../models/task';

type TaskChangeEvent = {
    task: Task;
    index: number;
};

export default TaskChangeEvent;
