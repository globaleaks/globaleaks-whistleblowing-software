import {ChangeDetectionStrategy, Component, inject} from "@angular/core";
import {TranslatePipe} from "@ngx-translate/core";
import {Router, RouterLink, RouterLinkActive} from "@angular/router";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";


@Component({
    selector: "src-admin-sidebar",
    templateUrl: "./sidebar.component.html",
    changeDetection: ChangeDetectionStrategy.OnPush,
    standalone: true,
    imports: [TranslatePipe, RouterLink, RouterLinkActive]
})
export class AdminSidebarComponent {
  private router = inject(Router);
  protected nodeResolver = inject(NodeResolver);
  protected authenticationService = inject(AuthenticationService);
  protected preferenceResolver = inject(PreferenceResolver);

  get permissions() {
    return this.preferenceResolver.dataModel.profile.permissions;
  }

  isActive(route: string): boolean {
    return this.router.isActive(route, {
      paths: "subset",
      queryParams: "subset",
      fragment: "ignored",
      matrixParams: "ignored"
    });
  }
}