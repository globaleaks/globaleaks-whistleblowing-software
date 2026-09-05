import {Component, computed, inject, ChangeDetectionStrategy} from "@angular/core";
import {TranslatePipe} from "@ngx-translate/core";
import {networkResolverModel} from "@app/models/resolvers/network-resolver-model";
import {NetworkResolver} from "@app/shared/resolvers/network.resolver";
import {HttpService} from "@app/shared/services/http.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {FormsModule} from "@angular/forms";


@Component({
    changeDetection: ChangeDetectionStrategy.OnPush,
    selector: "src-access-control",
    templateUrl: "./access-control.component.html",
    standalone: true,
    imports: [TranslatePipe, FormsModule]
})
export class AccessControlComponent {
  private readonly networkResolver = inject(NetworkResolver);
  private readonly httpService = inject(HttpService);
  private readonly utilsService = inject(UtilsService);

  readonly networkData = computed(() => this.networkResolver.resource.value());

  updateAccessControl(network: networkResolverModel) {
    this.httpService.requestUpdateNetworkResource(network).subscribe(() => {
      this.utilsService.reloadComponent();
    });
  }
}