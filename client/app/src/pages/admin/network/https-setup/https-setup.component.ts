import {Component, inject, output, ChangeDetectionStrategy} from "@angular/core";
import {TranslatePipe} from "@ngx-translate/core";
import {FileResources} from "@app/models/component-model/file-resources";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {HttpService} from "@app/shared/services/http.service";

@Component({
    changeDetection: ChangeDetectionStrategy.OnPush,
    selector: "src-https-setup",
    templateUrl: "./https-setup.component.html",
    standalone: true,
    imports: [TranslatePipe]
})
export class HttpsSetupComponent {
  private httpService = inject(HttpService);
  private authenticationService = inject(AuthenticationService);

  readonly updated = output<string | void>();
  fileResources: FileResources = {
    key: {name: "key"},
    cert: {name: "cert"},
    chain: {name: "chain"},
    csr: {name: "csr"},
  };

  setupAcme() {
    const authHeader = this.authenticationService.getHeader();
    this.httpService.requestUpdateTlsConfigFilesResource("key", authHeader, this.fileResources.key).subscribe(() => {
      this.httpService.requestAdminAcmeResource(Object, authHeader).subscribe(() => {
        this.updated.emit();
      });
    });
  }

  setup() {
    this.updated.emit("files");
  }
}
