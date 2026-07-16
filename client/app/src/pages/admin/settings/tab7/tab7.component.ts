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

  isInheritedTenantContext() {
    return !!this.nodeResolver.dataModel.tid && this.nodeResolver.dataModel.tid !== 1 && !this.nodeResolver.dataModel.is_profile;
  }

  updateNode() {
    if (this.nodeResolver.dataModel.idp && !this.nodeResolver.dataModel.idp_issuer) {
      return;
    }
    
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
