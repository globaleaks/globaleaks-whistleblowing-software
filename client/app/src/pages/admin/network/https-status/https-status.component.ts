import { Component, EventEmitter, Input, OnInit, Output, inject } from "@angular/core";
import {NetworkResolver} from "@app/shared/resolvers/network.resolver";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {nodeResolverModel} from "@app/models/resolvers/node-resolver-model";
import {TlsConfig} from "@app/models/component-model/tls-confiq";

import { TranslatorPipe } from "@app/shared/pipes/translate";

@Component({
    selector: "src-https-status",
    templateUrl: "./https-status.component.html",
    standalone: true,
    imports: [TranslatorPipe]
})
export class HttpsStatusComponent implements OnInit {
  protected networkResolver = inject(NetworkResolver);
  private nodeResolver = inject(NodeResolver);

  @Output() dataToParent = new EventEmitter<string>();
  @Input() tlsConfig: TlsConfig;
  nodeData: nodeResolverModel;

  ngOnInit(): void {
    this.nodeData = this.nodeResolver.dataModel;
  }

  getNetworkResolver(){
    return "https://" + this.networkResolver.dataModel.hostname
  }
}
