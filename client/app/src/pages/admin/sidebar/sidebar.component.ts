import { ChangeDetectionStrategy, Component, inject } from "@angular/core";
import { Router, RouterLink, RouterLinkActive } from "@angular/router";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";

import { TranslatorPipe } from "@app/shared/pipes/translate";

@Component({
    selector: "src-admin-sidebar",
    templateUrl: "./sidebar.component.html",
    changeDetection: ChangeDetectionStrategy.OnPush,
    standalone: true,
    imports: [RouterLink, RouterLinkActive, TranslatorPipe]
})
export class AdminSidebarComponent {
  private router = inject(Router);
  protected nodeResolver = inject(NodeResolver);
  protected authenticationService = inject(AuthenticationService);


  isActive(route: string): boolean {
    return this.router.isActive(route, {
      paths: "subset",
      queryParams: "subset",
      fragment: "ignored",
      matrixParams: "ignored"
    });
  }
}