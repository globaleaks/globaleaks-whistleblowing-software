import {Component, inject} from "@angular/core";
import {TranslatePipe} from "@ngx-translate/core";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";

@Component({
    selector: "src-license",
    templateUrl: "./license.component.html",
    standalone: true,
    imports: [TranslatePipe]
})
export class LicenseComponent {
  protected nodeResolver = inject(NodeResolver);
}
