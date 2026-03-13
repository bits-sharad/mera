import { HTTP_INTERCEPTORS } from '@angular/common/http';
import { NgModule } from '@angular/core';

import HttpRetryConfig from './http-resilient/http-retry.config';
import HttpRetryInterceptor from './http-resilient/http-retry.interceptor';

@NgModule({
    providers: [
        {
            provide: HTTP_INTERCEPTORS,
            useClass: HttpRetryInterceptor,
            multi: true,
        },
        { provide: HttpRetryInterceptor.HTTP_RETRY_CONFIG, useValue: HttpRetryConfig },
    ],
})
export default class AngularUtilsModule {}
