import { Component, inject } from "@angular/core";
import {AppConfigService} from "@app/services/root/app-config.service";
import {AppDataService} from "@app/app-data.service";

import { UserComponent } from "./template/user/user.component";
import { TranslateModule } from "@ngx-translate/core";
import { TranslatorPipe } from "@app/shared/pipes/translate";

@Component({
    selector: "views-header",
    templateUrl: "./header.component.html",
    standalone: true,
    imports: [UserComponent, TranslateModule, TranslatorPipe]
})
export class HeaderComponent {
  appConfig = inject(AppConfigService);
  appDataService = inject(AppDataService);
}
