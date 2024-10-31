import {Component, OnInit, inject} from "@angular/core";
import {nodeResolverModel} from "@app/models/resolvers/node-resolver-model";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import {FormsModule} from "@angular/forms";
import {TranslatorPipe} from "@app/shared/pipes/translate";

@Component({
    selector: "src-users-tab2",
    templateUrl: "./users-tab2.component.html",
    standalone: true,
    imports: [FormsModule, TranslatorPipe]
})
export class UsersTab2Component implements OnInit {
  private nodeResolver = inject(NodeResolver);
  private utilsService = inject(UtilsService);

  nodeData: nodeResolverModel;

  ngOnInit(): void {
    if (this.nodeResolver.dataModel) {
      this.nodeData = this.nodeResolver.dataModel;
    }
  }

  updateNode() {
    this.utilsService.update(this.nodeData).subscribe(_ => {
      this.utilsService.reloadComponent();
    });
  }
}