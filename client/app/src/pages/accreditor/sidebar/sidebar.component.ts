import { ChangeDetectionStrategy, Component } from '@angular/core';
import { Router } from '@angular/router';
import { AuthenticationService } from '@app/services/helper/authentication.service';
import { NodeResolver } from '@app/shared/resolvers/node.resolver';

@Component({
  selector: "src-accreditor-sidebar",
  templateUrl: "./sidebar.component.html",
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class SidebarComponent {

  constructor(private router: Router, protected nodeResolver: NodeResolver, protected authenticationService: AuthenticationService) {
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