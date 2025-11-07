import {Component, inject} from "@angular/core";
import {Router, RouterLink, RouterLinkActive} from "@angular/router";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
@Component({
    selector: "src-custodian-sidebar",
    templateUrl: "./sidebar.component.html",
    standalone: true,
    imports: [RouterLink, RouterLinkActive, TranslateModule, TranslatorPipe]
})
export class CustodianSidebarComponent {
  private router = inject(Router);
  protected nodeResolver = inject(NodeResolver);

  isActive(route: string): boolean {
    return this.router.isActive(route, {
      paths: "subset",
      queryParams: "subset",
      fragment: "ignored",
      matrixParams: "ignored"
    });
  }
}
