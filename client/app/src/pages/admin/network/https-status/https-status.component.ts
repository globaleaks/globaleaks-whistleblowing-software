import {Component, OnInit, inject, output, input, ChangeDetectionStrategy} from "@angular/core";
import {TranslatePipe} from "@ngx-translate/core";
import {NetworkResolver} from "@app/shared/resolvers/network.resolver";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {nodeResolverModel} from "@app/models/resolvers/node-resolver-model";
import {TlsConfig} from "@app/models/component-model/tls-confiq";


@Component({
    changeDetection: ChangeDetectionStrategy.OnPush,
    selector: "src-https-status",
    templateUrl: "./https-status.component.html",
    standalone: true,
    imports: [TranslatePipe]
})
export class HttpsStatusComponent implements OnInit {
  protected networkResolver = inject(NetworkResolver);
  private readonly nodeResolver = inject(NodeResolver);

  readonly updated = output<string>();
  readonly tlsConfig = input.required<TlsConfig>();
  nodeData: nodeResolverModel;

  ngOnInit(): void {
    this.nodeData = this.nodeResolver.dataModel;
  }

  getNetworkResolver(){
    return "https://" + this.networkResolver.resource.value().hostname
  }
}
