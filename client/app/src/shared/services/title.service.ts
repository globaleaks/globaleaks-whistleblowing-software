import {Injectable, Injector, inject} from '@angular/core';
import {AppDataService} from "@app/app-data.service";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {TranslateService} from "@ngx-translate/core";
import {Router} from "@angular/router";

@Injectable({
  providedIn: 'root'
})
export class TitleService {
  private readonly appDataService = inject(AppDataService);
  private readonly translateService = inject(TranslateService);
  private readonly router = inject(Router);

  // The node is resolved lazily: this service is reached from the
  // authentication, which the resolver of the node is reached through in turn
  private readonly injector = inject(Injector);

  private get isProfile(): boolean {
    return !!this.injector.get(NodeResolver).dataModel.is_profile;
  }


  public setPage(page: string) {
    this.appDataService.page = page;
    this.setTitle();
  };

  setTitle() {
    const {public: rootData} = this.appDataService;

    if (!rootData || !rootData.node) {
      return;
    }

    // A profile is not a site and holds no reporting people: whoever
    // administers one is told so by the title itself
    const projectTitle = this.isProfile ?
      this.translateService.instant('Profile') + ': ' + rootData.node.name :
      rootData.node.name;

    let pageTitle = rootData.node.header_title_homepage;


    if (this.appDataService.header_title && this.router.url !== "/") {
      pageTitle = this.appDataService.header_title;
    } else if (this.appDataService.page === "receiptpage") {
      pageTitle = "Your report was successful.";
    }

    if (pageTitle && pageTitle.length > 0) {
      pageTitle = pageTitle ? this.translateService.instant(pageTitle) : '';
    }

    this.appDataService.projectTitle = projectTitle !== "GLOBALEAKS" ? projectTitle : "";
    this.appDataService.pageTitle = pageTitle !== projectTitle ? pageTitle : "";

    if (pageTitle) {
      const finalPageTitle = pageTitle ? this.translateService.instant(pageTitle) : projectTitle;
      window.document.title = `${projectTitle} - ${finalPageTitle}`;

      const element = window.document.querySelector("meta[name=\"description\"]");
      if (element instanceof HTMLMetaElement) {
        element.content = rootData.node.description;
      }
    } else {
      window.document.title = projectTitle;
    }
  }
}
