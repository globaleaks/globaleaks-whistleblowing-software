import {Component, inject} from "@angular/core";
import {Router, RouterLink, RouterLinkActive} from "@angular/router";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {NgClass} from "@angular/common";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";

@Component({
    selector: "src-receipt-sidebar",
    templateUrl: "./sidebar.component.html",
    standalone: true,
    imports: [RouterLink, RouterLinkActive, NgClass, TranslateModule, TranslatorPipe]
})
export class ReceiptSidebarComponent {
  private router = inject(Router);
  protected preferenceResolver = inject(PreferenceResolver);
  protected nodeResolver = inject(NodeResolver);

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
