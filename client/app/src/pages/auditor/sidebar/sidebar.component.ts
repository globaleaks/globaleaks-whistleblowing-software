import {Component, inject} from "@angular/core";
import {Router, RouterLink, RouterLinkActive} from "@angular/router";
import {TranslatePipe} from "@ngx-translate/core";

@Component({
    selector: "src-auditor-sidebar",
    templateUrl: "./sidebar.component.html",
    standalone: true,
    imports: [RouterLink, RouterLinkActive, TranslatePipe]
})
export class AuditorSidebarComponent {
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
