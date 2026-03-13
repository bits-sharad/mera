import { Component } from '@angular/core';

import webComponentList from './web-components.json';

@Component({
    selector: 'polaris-gallery',
    templateUrl: './gallery.component.html',
    styleUrls: ['./gallery.component.scss'],
    standalone: false,
})
export default class GalleryComponent {
    links = webComponentList;
}
