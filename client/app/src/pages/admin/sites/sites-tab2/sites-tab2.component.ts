import { Component, inject } from "@angular/core";
import {QuestionnairesResolver} from "@app/shared/resolvers/questionnaires.resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import { FormsModule } from "@angular/forms";

import { TranslatorPipe } from "@app/shared/pipes/translate";
import { TranslateModule } from "@ngx-translate/core";

@Component({
    selector: "src-sites-tab2",
    templateUrl: "./sites-tab2.component.html",
    standalone: true,
    imports: [FormsModule, TranslatorPipe, TranslateModule]
})
export class SitesTab2Component {
  protected nodeResolver = inject(NodeResolver);
  protected utilsService = inject(UtilsService);
  questionnairesResolver = inject(QuestionnairesResolver);
}