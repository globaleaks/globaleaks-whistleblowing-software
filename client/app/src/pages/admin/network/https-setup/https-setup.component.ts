import {Component, EventEmitter, Output, inject} from "@angular/core";
import {FileResources} from "@app/models/component-model/file-resources";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {HttpService} from "@app/shared/services/http.service";
import {TranslatorPipe} from "@app/shared/pipes/translate";

@Component({
    selector: "src-https-setup",
    templateUrl: "./https-setup.component.html",
    standalone: true,
    imports: [TranslatorPipe]
})
export class HttpsSetupComponent {
  private httpService = inject(HttpService);
  private authenticationService = inject(AuthenticationService);

  @Output() dataToParent = new EventEmitter<string>();
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
        this.dataToParent.emit();
      });
    });
  }

  setup() {
    this.dataToParent.emit("files");
  }
}