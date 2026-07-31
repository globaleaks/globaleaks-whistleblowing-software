import {Component, inject} from "@angular/core";
import {UtilsService} from "@app/shared/services/utils.service";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {FormsModule} from "@angular/forms";

import {TranslatorPipe} from "@app/shared/pipes/translate";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-sites-tab3",
    templateUrl: "./sites-tab3.component.html",
    standalone: true,
    imports: [FormsModule, TranslatorPipe, TranslateModule]
})
export class SitesTab3Component {
  protected nodeResolver = inject(NodeResolver);
  protected utilsService = inject(UtilsService);
}
