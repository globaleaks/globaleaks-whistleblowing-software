import {Component, Input, inject, OnInit} from "@angular/core";
import {FormsModule, NgForm} from "@angular/forms";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {TranslateModule} from "@ngx-translate/core";
import {UtilsService} from "@app/shared/services/utils.service";
import {AppConfigService} from "@app/services/root/app-config.service";

@Component({
    selector: "src-tab5",
    templateUrl: "./tab5.component.html",
    standalone: true,
    imports: [FormsModule, TranslatorPipe, TranslateModule]
})
export class Tab5Component implements OnInit {
  protected nodeResolver = inject(NodeResolver);
  private utilsService = inject(UtilsService);
  private appConfigService = inject(AppConfigService);
  private readonly defaultClamdIp = "localhost";
  private readonly defaultClamdPort = 3310;

  @Input() contentForm: NgForm;

  ngOnInit(): void {
    this.applyDefaultClamdEndpoint();
  }

  private applyDefaultClamdEndpoint(): void {
    const clamdIp = this.nodeResolver.dataModel.antivirus_clamd_ip?.trim();
    this.nodeResolver.dataModel.antivirus_clamd_ip = clamdIp || this.defaultClamdIp;

    if (!this.nodeResolver.dataModel.antivirus_clamd_port || this.nodeResolver.dataModel.antivirus_clamd_port < 1) {
      this.nodeResolver.dataModel.antivirus_clamd_port = this.defaultClamdPort;
    }
  }

  save(): void {
    this.applyDefaultClamdEndpoint();
    this.utilsService.update(this.nodeResolver.dataModel).subscribe(_ => {
      this.appConfigService.reinit();
      this.utilsService.reloadComponent();
    });
  }
}
