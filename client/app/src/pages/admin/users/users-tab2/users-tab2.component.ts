import {Component, OnInit, inject} from "@angular/core";
import {TranslatePipe} from "@ngx-translate/core";
import {nodeResolverModel} from "@app/models/resolvers/node-resolver-model";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import {FormsModule} from "@angular/forms";

@Component({
    selector: "src-users-tab2",
    templateUrl: "./users-tab2.component.html",
    standalone: true,
    imports: [TranslatePipe, FormsModule]
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
    this.utilsService.update(this.nodeData).subscribe(() => {
      this.utilsService.reloadComponent();
    });
  }
}