import { ComponentFixture, TestBed } from '@angular/core/testing';

import MMCBrandComponent from './mmc-brand.component';

describe('MMCBrandComponent', () => {
    let component: MMCBrandComponent;
    let fixture: ComponentFixture<MMCBrandComponent>;

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [MMCBrandComponent],
        }).compileComponents();

        fixture = TestBed.createComponent(MMCBrandComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });
});
