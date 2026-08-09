import {Component, inject, input, OnInit} from "@angular/core";
import {FormsModule, NgForm} from "@angular/forms";
import {nodeResolverModel} from "@app/models/resolvers/node-resolver-model";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {TranslateModule} from "@ngx-translate/core";
import {UtilsService} from "@app/shared/services/utils.service";
import {AppConfigService} from "@app/services/root/app-config.service";

@Component({
    selector: "src-tab7",
    templateUrl: "./tab7.component.html",
    standalone: true,
    imports: [FormsModule, TranslateModule]
})
export class Tab7Component implements OnInit {
  readonly contentForm = input.required<NgForm>();
  nodeData: nodeResolverModel;

  private readonly defaultClamdIp = "localhost";
  private readonly defaultClamdPort = 3310;

  protected utilsService = inject(UtilsService);
  private nodeResolver = inject(NodeResolver);
  private appConfigService = inject(AppConfigService);

  ngOnInit(): void {
    this.nodeData = this.nodeResolver.dataModel;
    this.applyDefaultClamdEndpoint();
  }

  private applyDefaultClamdEndpoint(): void {
    const clamdIp = this.nodeData.antivirus_clamd_ip?.trim();
    this.nodeData.antivirus_clamd_ip = clamdIp || this.defaultClamdIp;

    if (!this.nodeData.antivirus_clamd_port || this.nodeData.antivirus_clamd_port < 1) {
      this.nodeData.antivirus_clamd_port = this.defaultClamdPort;
    }
  }

  save(): void {
    this.applyDefaultClamdEndpoint();
    this.utilsService.update(this.nodeResolver.dataModel).subscribe(() => {
      this.appConfigService.reinit();
    });
  }

  toggleAntivirus(): void {
    this.nodeData.antivirus_enabled = !this.nodeData.antivirus_enabled;
    this.save();
  }

  resetAntivirus(): void {
    this.nodeData.antivirus_enabled = false;
    this.nodeData.antivirus_clamd_ip = this.defaultClamdIp;
    this.nodeData.antivirus_clamd_port = this.defaultClamdPort;
    this.save();
  }
}
