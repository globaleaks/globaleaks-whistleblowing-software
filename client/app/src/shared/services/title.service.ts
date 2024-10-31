import {Injectable, inject} from '@angular/core';
import {AppDataService} from "@app/app-data.service";
import {TranslateService} from "@ngx-translate/core";
import {Router} from "@angular/router";

@Injectable({
  providedIn: 'root'
})
export class TitleService {
  private appDataService = inject(AppDataService);
  private translateService = inject(TranslateService);
  private router = inject(Router);


  public setPage(page: string) {
    this.appDataService.page = page;
    this.setTitle();
  };

  setTitle() {
    const {public: rootData} = this.appDataService;

    if (!rootData || !rootData.node) {
      return;
    }

    const projectTitle = rootData.node.name;
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
