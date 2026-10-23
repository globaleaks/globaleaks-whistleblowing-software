import {Component, inject} from "@angular/core";
import {Router, RouterLink, RouterLinkActive} from "@angular/router";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {TranslatePipe} from "@ngx-translate/core";

@Component({
    selector: "src-receipt-sidebar",
    templateUrl: "./sidebar.component.html",
    standalone: true,
    imports: [RouterLink, RouterLinkActive, TranslatePipe]
})
export class ReceiptSidebarComponent {
  private router = inject(Router);
  protected preferenceResolver = inject(PreferenceResolver);

  message: string;

  isActive(route: string): boolean {
    return this.router.isActive(route, {
      paths: "subset",
      queryParams: "subset",
      fragment: "ignored",
      matrixParams: "ignored"
    });
  }
}
