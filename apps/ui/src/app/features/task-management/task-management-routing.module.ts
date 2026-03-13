import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

import TaskManagementComponent from './task-management.component';

const routes: Routes = [{ path: '', component: TaskManagementComponent }];

@NgModule({
    imports: [RouterModule.forChild(routes)],
    exports: [RouterModule],
})
export default class TaskManagementRoutingModule {}
