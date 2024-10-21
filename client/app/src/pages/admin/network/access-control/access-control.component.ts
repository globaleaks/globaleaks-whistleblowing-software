import { Component, OnInit, inject } from "@angular/core";
import {networkResolverModel} from "@app/models/resolvers/network-resolver-model";
import {NetworkResolver} from "@app/shared/resolvers/network.resolver";
import {HttpService} from "@app/shared/services/http.service";
import {UtilsService} from "@app/shared/services/utils.service";
import { FormsModule } from "@angular/forms";

import { TranslatorPipe } from "@app/shared/pipes/translate";

@Component({
    selector: "src-access-control",
    templateUrl: "./access-control.component.html",
    standalone: true,
    imports: [FormsModule, TranslatorPipe]
})
export class AccessControlComponent implements OnInit {
  private networkResolver = inject(NetworkResolver);
  private httpService = inject(HttpService);
  private utilsService = inject(UtilsService);

  networkData: networkResolverModel;

  ngOnInit(): void {
    this.networkData = this.networkResolver.dataModel;
  }

  updateAccessControl(network: networkResolverModel) {
    this.httpService.requestUpdateNetworkResource(network).subscribe(() => {
      this.utilsService.reloadComponent();
    });
  }
}