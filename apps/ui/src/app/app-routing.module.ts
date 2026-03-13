import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { OktaAuthGuard } from '@okta/okta-angular';

// Although this is a workaround for Cypress, it is advised to create a change order
// for service accounts that may login to Okta, and Cypress must go through Okta validation before testing the flow.
import { isTestEnvironment } from '@jobmatchingmodelpoc/shared-angular-utils/auth/auth.interceptor';

import GalleryComponent from './features/gallery/gallery.component';
import MMCBrandComponent from './features/mmc-brand/mmc-brand.component';
import TaskAddComponent from './features/task-management/components/task-add/task-add.component';
import OktaCallbackComponent from './okta-callback/okta-callback.component';

export const routes: Routes = [
    {
        path: '',
        loadChildren: () => import('./features/home/home.module').then((m) => m.default),
        canActivate: isTestEnvironment ? [] : [OktaAuthGuard],
    },
    {
        path: 'tasks',
        loadChildren: () =>
            import('./features/task-management/task-management.module').then((m) => m.default),
        canActivate: isTestEnvironment ? [] : [OktaAuthGuard],
    },
    {
        path: 'tasks/add',
        component: TaskAddComponent,
        canActivate: isTestEnvironment ? [] : [OktaAuthGuard],
    },
    {
        path: 'tasks/edit/:id',
        component: TaskAddComponent,
        canActivate: isTestEnvironment ? [] : [OktaAuthGuard],
    },
    {
        path: 'mmc-brand',
        component: MMCBrandComponent,
    },
    {
        path: 'gallery',
        component: GalleryComponent,
    },
    // Map the callback route to the OktaCallbackComponent, which handles any tokens returned from the login process
    { path: 'login/callback', component: OktaCallbackComponent },
];

@NgModule({
    imports: [RouterModule.forRoot(routes)],
    exports: [RouterModule],
})
export default class AppRoutingModule {}
