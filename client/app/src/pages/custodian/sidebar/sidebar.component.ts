import {Component, inject, ChangeDetectionStrategy} from "@angular/core";
import {RouterLink, RouterLinkActive} from "@angular/router";
import {TranslatePipe} from "@ngx-translate/core";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
@Component({
    changeDetection: ChangeDetectionStrategy.OnPush,
    selector: "src-custodian-sidebar",
    templateUrl: "./sidebar.component.html",
    standalone: true,
    imports: [RouterLink, RouterLinkActive, TranslatePipe]
})
export class CustodianSidebarComponent {
  protected nodeResolver = inject(NodeResolver);

}
