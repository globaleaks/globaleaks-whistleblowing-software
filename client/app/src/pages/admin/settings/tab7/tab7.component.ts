import {Component, Input, inject} from "@angular/core";
import {FormsModule, NgForm} from "@angular/forms";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {NgClass} from "@angular/common";
import {TranslateModule} from "@ngx-translate/core";
import {UtilsService} from "@app/shared/services/utils.service";
import {Constants} from "@app/shared/constants/constants";
import {AppConfigService} from "@app/services/root/app-config.service";
import {AppDataService} from "@app/app-data.service";

@Component({
    selector: "src-tab7",
    templateUrl: "./tab7.component.html",
    standalone: true,
    imports: [FormsModule, NgClass, TranslateModule]
})
export class Tab7Component {
  @Input() contentForm: NgForm;

  private utilsService = inject(UtilsService);
  private appConfigService = inject(AppConfigService);
  private appDataService = inject(AppDataService);
  protected nodeResolver = inject(NodeResolver);
  protected readonly Constants = Constants;

  constructor() {
    this.nodeResolver.dataModel.auth_type = this.nodeResolver.dataModel.idp ? 'idp' : 'globaleaks';
  }

  updateNode() {
    this.nodeResolver.dataModel.idp = this.nodeResolver.dataModel.auth_type === "idp";
    // The issuer is validated server-side during the update: the backend checks
    // that it is reachable and exposes a usable JWKS and returns an error
    // otherwise (surfaced by the global error interceptor).
    this.utilsService.update(this.nodeResolver.dataModel).subscribe({
      next: () => {
        if (this.appDataService.public?.node) {
          this.appDataService.updatePublic({
            ...this.appDataService.public,
            node: {
              ...this.appDataService.public.node,
              idp: this.nodeResolver.dataModel.idp,
              idp_issuer: this.nodeResolver.dataModel.idp_issuer
            }
          });
        }
        this.appConfigService.reinit(false);
      }
    });
  }
}
