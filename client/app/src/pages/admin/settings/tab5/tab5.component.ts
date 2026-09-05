import {Component, Input, OnInit, inject} from "@angular/core";
import {FormsModule, NgForm} from "@angular/forms";
import {nodeResolverModel} from "@app/models/resolvers/node-resolver-model";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {TranslateModule} from "@ngx-translate/core";
import {UtilsService} from "@app/shared/services/utils.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {AppConfigService} from "@app/services/root/app-config.service";
import {AppDataService} from "@app/app-data.service";

@Component({
    selector: "src-tab5",
    templateUrl: "./tab5.component.html",
    standalone: true,
    imports: [FormsModule, TranslateModule]
})
export class Tab5Component implements OnInit {
  @Input() contentForm: NgForm;
  nodeData: nodeResolverModel;
  idpEnabled = false;
  idpIssuer = "";
  idpClientId = "";
  idpProvisioning = false;

  protected utilsService = inject(UtilsService);
  private readonly authenticationService = inject(AuthenticationService);
  private readonly appConfigService = inject(AppConfigService);
  private readonly appDataService = inject(AppDataService);
  private readonly nodeResolver = inject(NodeResolver);

  ngOnInit(): void {
    this.nodeData = this.nodeResolver.dataModel;
    this.loadIdpConfiguration();
  }

  loadIdpConfiguration() {
    this.idpEnabled = this.nodeData.idp;
    this.idpIssuer = this.nodeData.idp_issuer;
    this.idpClientId = this.nodeData.idp_client_id;
    this.idpProvisioning = this.nodeData.idp_provisioning;
  }

  isInheritedTenantContext() {
    // The default profile seeds the initialization and carries the defaults: a tenant on it inherits
    // no managed configuration
    return !!this.nodeData.tid && this.nodeData.tid !== 1 && !this.nodeData.is_profile &&
           this.nodeData.profile !== "default";
  }

  isConfigurationValid() {
    return !!this.idpIssuer && !!this.idpClientId;
  }

  isLocked() {
    // The configuration can be modified only while in the Disabled state
    return this.isInheritedTenantContext() || this.nodeData.idp;
  }

  save(): void {
    this.nodeData.idp = this.idpEnabled;
    this.nodeData.idp_issuer = this.idpIssuer;
    this.nodeData.idp_client_id = this.idpClientId;
    this.nodeData.idp_provisioning = this.idpProvisioning;

    this.utilsService.update(this.nodeData).subscribe({
      next: () => {
        if (this.appDataService.public?.node) {
          this.appDataService.updatePublic({
            ...this.appDataService.public,
            node: {
              ...this.appDataService.public.node,
              idp: this.nodeData.idp,
              idp_issuer: this.nodeData.idp_issuer,
              idp_client_id: this.nodeData.idp_client_id
            }
          });
        }
        this.appConfigService.reinit();
      }
    });
  }

  enableIdp(): void {
    // Validated only for the platform the administrator operates as its own
    if (this.nodeData.is_profile || this.authenticationService.session?.properties?.management_session) {
      this.idpEnabled = true;
      this.save();
      return;
    }

    // Enabled only if the issuer exists, is reachable and recognizes the client: the backend
    // validates it
    this.utilsService.runAdminOperation("validate_idp", {"issuer": this.idpIssuer, "client_id": this.idpClientId}, false).subscribe({
      next: () => {
        this.idpEnabled = true;
        this.save();
      }
    });
  }

  disableIdp(): void {
    this.idpEnabled = false;
    this.save();
  }

  resetIdp(): void {
    this.idpEnabled = false;
    this.idpIssuer = "";
    this.idpClientId = "";
    this.idpProvisioning = false;
    this.save();
  }
}
