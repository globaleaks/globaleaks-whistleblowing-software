// https://github.com/globaleaks/GlobaLeaks/issues/3277
// Create a proxy to override localStorage methods with sessionStorage methods
(function() {
  const localStorageProxy = {
    getItem: (key: string) => sessionStorage.getItem(key),
    setItem: (key: string, value: string) => sessionStorage.setItem(key, value),
    removeItem: (key: string) => sessionStorage.removeItem(key),
    clear: () => sessionStorage.clear(),
    key: (index: number) => sessionStorage.key(index),
    get length() {
      return sessionStorage.length;
    }
  };

  // Assign the proxy to localStorage
  Object.defineProperty(window, 'localStorage', {
    value: localStorageProxy,
    configurable: false,
    writable: false
  });
})();

import {platformBrowserDynamic} from "@angular/platform-browser-dynamic";
import {AppModule} from "@app/app.module";

platformBrowserDynamic().bootstrapModule(AppModule)
  .catch(err => console.error(err));
