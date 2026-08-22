import {Component, inject, ChangeDetectionStrategy} from "@angular/core";
import {Router, RouterLink, RouterLinkActive} from "@angular/router";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    changeDetection: ChangeDetectionStrategy.OnPush,
    selector: "src-custodian-sidebar",
    templateUrl: "./sidebar.component.html",
    standalone: true,
    imports: [RouterLink, RouterLinkActive, TranslateModule]
})
export class CustodianSidebarComponent {
  private router = inject(Router);

  isActive(route: string): boolean {
    return this.router.isActive(route, {
      paths: "subset",
      queryParams: "subset",
      fragment: "ignored",
      matrixParams: "ignored"
    });
  }
}
