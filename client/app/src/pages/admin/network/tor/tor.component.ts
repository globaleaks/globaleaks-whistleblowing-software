import {Component, OnInit, inject} from "@angular/core";
import {networkResolverModel} from "@app/models/resolvers/network-resolver-model";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {HttpService} from "@app/shared/services/http.service";
import {UtilsService} from "@app/shared/services/utils.service";

import {FormsModule} from "@angular/forms";
import {TranslatorPipe} from "@app/shared/pipes/translate";

@Component({
    selector: "src-tor",
    templateUrl: "./tor.component.html",
    standalone: true,
    imports: [FormsModule, TranslatorPipe]
})
export class TorComponent implements OnInit {
  protected nodeResolver = inject(NodeResolver);
  private httpService = inject(HttpService);
  private utilsService = inject(UtilsService);

  torOnionResetInProgress: boolean = false;
  networkData: networkResolverModel;

  ngOnInit(): void {
    this.getNetortResolver();
  }

  resetOnionPrivateKey() {
    return this.utilsService.runAdminOperation("reset_onion_private_key", {}, true).subscribe();
  }

  updateTor(network: networkResolverModel) {
    this.httpService.requestUpdateNetworkResource(network).subscribe(() => {
      this.utilsService.reloadComponent();
    });
  }

  getNetortResolver() {
    return this.httpService.requestNetworkResource().subscribe(response => {
        this.networkData = response;
    });
  }
}