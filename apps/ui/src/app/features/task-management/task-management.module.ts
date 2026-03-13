import { CommonModule } from '@angular/common';
import { NgModule } from '@angular/core';
import { FormsModule } from '@angular/forms';

import TaskComponent from './components/task/task.component';
import TaskAddComponent from './components/task-add/task-add.component';
import TaskDetailsComponent from './components/task-details/task-details.component';
import TaskListComponent from './components/task-list/task-list.component';
import TaskManagementService from './services/task-management.service';
import TaskManagementRoutingModule from './task-management-routing.module';
import TaskManagementComponent from './task-management.component';
import SharedModule from '../../shared/shared.module';

@NgModule({
    declarations: [
        TaskComponent,
        TaskDetailsComponent,
        TaskListComponent,
        TaskManagementComponent,
        TaskAddComponent,
    ],
    imports: [CommonModule, FormsModule, TaskManagementRoutingModule, SharedModule],
    providers: [TaskManagementService],
})
export default class TaskManagementModule {}
