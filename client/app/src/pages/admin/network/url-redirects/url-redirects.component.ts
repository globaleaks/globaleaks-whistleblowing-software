import {Component, OnInit, inject} from "@angular/core";
import {redirectResolverModel} from "@app/models/resolvers/redirect-resolver-model";
import {HttpService} from "@app/shared/services/http.service";
import {FormsModule} from "@angular/forms";

import {TranslatorPipe} from "@app/shared/pipes/translate";
import {OrderByPipe} from "@app/shared/pipes/order-by.pipe";

@Component({
    selector: "src-url-redirects",
    templateUrl: "./url-redirects.component.html",
    standalone: true,
    imports: [FormsModule, TranslatorPipe, OrderByPipe]
})
export class UrlRedirectsComponent implements OnInit {
  private httpService = inject(HttpService);

  redirectData: redirectResolverModel[];
  new_redirect = {
    path1: "",
    path2: ""
  };

  ngOnInit(): void {
    this.getResolver();
  }

  redirectPath(path: redirectResolverModel, index: number) {
    if (index === 1) {
      return path.path1;
    } else {
      return path.path2;
    }
  }

  addRedirect() {
    const arg = {
      path1: this.new_redirect.path1,
      path2: this.new_redirect.path2
    };
    this.httpService.requestPostRedirectsResource(arg).subscribe((res) => {
      this.redirectData.push(res);
      this.new_redirect.path1 = "";
      this.new_redirect.path2 = "";
      this.getResolver();
    });
  }

  getResolver() {
    return this.httpService.requestRedirectsResource().subscribe(response => {
      if (Array.isArray(response)) {
        this.redirectData = response;
      } else {
        this.redirectData = [response];
      }
    });
  }

  deleteRedirect(redirect: redirectResolverModel) {
    this.httpService.requestDeleteRedirectsResource(redirect.id).subscribe(() => {
      this.getResolver();
    });
  }
}