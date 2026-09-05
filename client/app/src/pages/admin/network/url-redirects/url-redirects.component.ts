import {Component, OnInit, inject} from "@angular/core";
import {TranslatePipe} from "@ngx-translate/core";
import {redirectResolverModel} from "@app/models/resolvers/redirect-resolver-model";
import {HttpService} from "@app/shared/services/http.service";
import {FormsModule} from "@angular/forms";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {PaginatedInterfaceComponent} from "@app/shared/components/paginated-interface/paginated-interface.component";

@Component({
    selector: "src-url-redirects",
    templateUrl: "./url-redirects.component.html",
    standalone: true,
    imports: [TranslatePipe, FormsModule, NgbTooltipModule, PaginatedInterfaceComponent]
})
export class UrlRedirectsComponent implements OnInit {
  private readonly httpService = inject(HttpService);

  redirectData: redirectResolverModel[] = [];
  showAddRedirect = false;
  new_redirect = {
    path1: "",
    path2: ""
  };

  ngOnInit(): void {
    this.getResolver();
  }

  toggleAddRedirect(): void {
    this.showAddRedirect = !this.showAddRedirect;
  }

  addRedirect() {
    const arg = {
      path1: this.new_redirect.path1,
      path2: this.new_redirect.path2
    };
    this.httpService.requestPostRedirectsResource(arg).subscribe(() => {
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
