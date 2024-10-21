import { Injectable, inject } from '@angular/core';
import {AppDataService} from "@app/app-data.service";

@Injectable({
  providedIn: 'root'
})
export class CustomFileLoaderServiceService {
  private appDataService = inject(AppDataService);


  loadCustomFiles(): void {
    if (window.location.pathname === '/' && this.appDataService.public.node) {
      let cssLoaded = false;
      let jsLoaded = false;

      const showBodyIfReady = () => {
        if (cssLoaded && jsLoaded) {
          document.body.style.display = 'block';
        }
      };

      if (this.appDataService.public.node.css) {
        document.body.style.display = 'none';
        const newElem = document.createElement('link');
        newElem.setAttribute('id', 'load-custom-css-new');
        newElem.setAttribute('rel', 'stylesheet');
        newElem.setAttribute('type', 'text/css');
        newElem.setAttribute('href', 's/css');
        document.getElementsByTagName('head')[0].appendChild(newElem);

        newElem.onload = () => {
          const oldElem = document.getElementById('load-custom-css');
          if (oldElem !== null && oldElem.parentNode !== null) {
            oldElem.parentNode.removeChild(oldElem);
          }
          newElem.setAttribute('id', 'load-custom-css');
          cssLoaded = true;
          showBodyIfReady();
        };
      } else {
        cssLoaded = true;
        showBodyIfReady();
      }

      if (this.appDataService.public.node.script) {
        document.body.style.display = 'none';
        const scriptElem = document.createElement('script');
        scriptElem.setAttribute('id', 'load-custom-script');
        scriptElem.setAttribute('src', 's/script');
        document.getElementsByTagName('body')[0].appendChild(scriptElem);

        scriptElem.onload = () => {
          jsLoaded = true;
          showBodyIfReady();
        };
      } else {
        jsLoaded = true;
        showBodyIfReady();
      }

      if (this.appDataService.public.node.favicon) {
        const faviconElem = window.document.getElementById('favicon');
        if (faviconElem !== null) {
          faviconElem.setAttribute('href', 's/favicon');
        }
      }
    }
  }
}
