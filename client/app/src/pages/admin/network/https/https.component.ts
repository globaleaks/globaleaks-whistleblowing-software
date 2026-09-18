import {Component, OnInit, inject} from "@angular/core";
import {TranslatePipe} from "@ngx-translate/core";
import {AppDataService} from "@app/app-data.service";
import {TlsConfig} from "@app/models/component-model/tls-confiq";
import {Constants} from "@app/shared/constants/constants";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {HttpService} from "@app/shared/services/http.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {FormsModule} from "@angular/forms";
import {HttpsStatusComponent} from "../https-status/https-status.component";
import {HttpsSetupComponent} from "../https-setup/https-setup.component";
import {HttpsFilesComponent} from "../https-files/https-files.component";

@Component({
    selector: "src-https",
    templateUrl: "./https.component.html",
    standalone: true,
    imports: [TranslatePipe, FormsModule, HttpsStatusComponent, HttpsSetupComponent, HttpsFilesComponent]
})
export class HttpsComponent implements OnInit {
  protected nodeResolver = inject(NodeResolver);
  private readonly httpService = inject(HttpService);
  private readonly utilsService = inject(UtilsService);
  protected appDataService = inject(AppDataService);

  protected readonly Constants = Constants;
  state = 0;
  menuState = "setup";
  tlsConfig: TlsConfig;
  hostName="";

  ngOnInit() {
    this.initFunction();
    this.hostName = this.appDataService.public.node.hostname
  }

  initFunction() {
    this.httpService.requestTlsConfigResource().subscribe(
      (config: TlsConfig) => {
        this.parseTLSConfig(config);
      }
    );
  }

  updateHostname(hostname: string) {
    this.utilsService.runAdminOperation("set_hostname", {"value": hostname}, true)
      .subscribe(
        () => {
          this.appDataService.public.node.hostname=this.hostName;
        }
      );
  }

  parseTLSConfig(tlsConfig: TlsConfig): void {
    this.tlsConfig = tlsConfig;

    let t = 0;
    let choice = "setup";

    if (!tlsConfig.acme) {
      if (tlsConfig.files.key.set) {
        t = 1;
      }

      if (tlsConfig.files.cert.set) {
        t = 2;
      }

      if (tlsConfig.files.chain.set) {
        t = 3;
      }
    } else if (
      tlsConfig.files.key.set &&
      tlsConfig.files.cert.set &&
      tlsConfig.files.chain.set
    ) {
      t = 3;
    }

    if (tlsConfig.enabled) {
      choice = "status";
      t = -1;
    } else if (t > 0) {
      choice = "files";
    }

    this.state = t;
    this.menuState = choice;
  }

  onUpdate(data: string | void) {
    if (data) {
      this.menuState = data;
    }
    if (!data) {
      this.initFunction();
    }
  }
}
