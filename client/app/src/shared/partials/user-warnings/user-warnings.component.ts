import {Component, inject} from "@angular/core";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";

import {TranslatePipe} from "@ngx-translate/core";

@Component({
    selector: "src-user-warnings",
    templateUrl: "./user-warnings.component.html",
    standalone: true,
    imports: [TranslatePipe]
})
export class UserWarningsComponent {
  protected authentication = inject(AuthenticationService);
  protected preferenceResolver = inject(PreferenceResolver);
  protected nodeResolver = inject(NodeResolver);
}
