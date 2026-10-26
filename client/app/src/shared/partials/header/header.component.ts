import {Component, inject} from "@angular/core";
import {AppConfigService} from "@app/services/root/app-config.service";
import {AppDataService} from "@app/app-data.service";

import {UserComponent} from "./template/user/user.component";
import {TranslatePipe} from "@ngx-translate/core";

@Component({
    selector: "src-header",
    templateUrl: "./header.component.html",
    standalone: true,
    imports: [UserComponent, TranslatePipe]
})
export class HeaderComponent {
  appConfig = inject(AppConfigService);
  appDataService = inject(AppDataService);
}
