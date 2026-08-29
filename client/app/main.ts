(function() {
  // Limit usage of setAttribute on 'stlyle'
  // This is intended to limit our own libraries to scatter CSP policies violations,
  // it is not intended as a block for an attacker that is already limited by the CSP.
  const originalSetAttribute = Element.prototype.setAttribute;

  Element.prototype.setAttribute = function(name, value) {
    if (name.toLowerCase() !== 'style') {
      originalSetAttribute.call(this, name, value);
    }
  };

  // https://github.com/globaleaks/GlobaLeaks/issues/3277
  // Create a proxy to override localStorage methods with sessionStorage methods
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

import '@app/icons';
import { mockEngine } from "@app/services/helper/mocks";
import { MarkdownRendererService } from '@app/services/helper/markdown.service';
import { provideTranslateService } from "@ngx-translate/core";
import { HTTP_INTERCEPTORS, withInterceptorsFromDi, provideHttpClient } from "@angular/common/http";
import { appInterceptor, ErrorCatchingInterceptor, CompletedInterceptor } from "@app/services/root/app-interceptor.service";
import { APP_BASE_HREF, LocationStrategy, HashLocationStrategy } from "@angular/common";
import { FlowInjectionToken } from "@flowjs/ngx-flow";
import { NgbDatepickerI18n, NgbPaginationConfig, NgbTooltipConfig } from "@ng-bootstrap/ng-bootstrap";
import { CustomDatepickerI18n } from "@app/shared/services/custom-datepicker-i18n";
import { appRoutes } from "@app/app.routes";
import { bootstrapApplication } from "@angular/platform-browser";
import { provideMarkdown, MARKED_OPTIONS } from "ngx-markdown";
import { AppComponent } from "@app/pages/app/app.component";
import { provideRouter } from "@angular/router";
import { ApplicationRef, enableProdMode, provideZonelessChangeDetection } from '@angular/core';
import { provideTranslateHttpLoader } from '@ngx-translate/http-loader';
import Flow from "@flowjs/flow.js";
import { provideOAuthClient } from "angular-oauth2-oidc";

enableProdMode();

bootstrapApplication(AppComponent, {
    providers: [
        provideZonelessChangeDetection(),
        provideRouter(appRoutes),
        provideMarkdown({
          markedOptions: {
            provide: MARKED_OPTIONS,
            useFactory: (rendererService: MarkdownRendererService) => ({
              breaks: true,
              renderer: rendererService.getCustomRenderer(),
            }),
            deps: [MarkdownRendererService]
          }
        }),
        provideTranslateService({
          loader: provideTranslateHttpLoader({prefix: "l10n/", suffix: ""}),
        }),
        { provide: APP_BASE_HREF, useValue: "/" },
        { provide: HTTP_INTERCEPTORS, useClass: appInterceptor, multi: true },
        { provide: HTTP_INTERCEPTORS, useClass: ErrorCatchingInterceptor, multi: true },
        { provide: HTTP_INTERCEPTORS, useClass: CompletedInterceptor, multi: true },
        { provide: FlowInjectionToken, useValue: Flow },
        { provide: LocationStrategy, useClass: HashLocationStrategy },
        { provide: NgbDatepickerI18n, useClass: CustomDatepickerI18n },
        {
          provide: NgbPaginationConfig,
          useFactory: () => {
            const config = new NgbPaginationConfig();
            config.size = 'sm';           // Set pagination size (sm for small, lg for large)
            config.boundaryLinks = true;  // Display boundary links (first/last)
            config.directionLinks = true; // Display previous/next buttons
            config.maxSize = 20;          // Maximum number of pages displayed
            config.rotate = true;         // Whether to rotate pages when maxSize > number of pages.
            config.ellipses = true;       // If true, the ellipsis symbols and first/last page numbers
                                          // will be shown when maxSize > number of pages.
            return config;
          }
        },
	{
          provide: NgbTooltipConfig,
          useFactory: () => {
            const config = new NgbTooltipConfig();
	    config.triggers = 'mouseenter:mouseleave';

	    return config;
	  }
        },
        { provide: 'MockEngine', useValue: mockEngine },
        provideOAuthClient(),
        provideHttpClient(withInterceptorsFromDi())
    ]
}).then(moduleRef => {
    // Expose Angular stability status to Cypress
    const appRef = moduleRef.injector.get(ApplicationRef);
    (window as any).isAngularStable = () => appRef.isStable;
})
  .catch(err => console.error(err));
