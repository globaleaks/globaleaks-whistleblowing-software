import {Component, Input, inject} from "@angular/core";
import {FormsModule, NgForm} from "@angular/forms";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {NgClass} from "@angular/common";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {TranslateModule} from "@ngx-translate/core";
import {UtilsService} from "@app/shared/services/utils.service";

@Component({
    selector: "src-tab6",
    templateUrl: "./tab6.component.html",
    standalone: true,
    imports: [FormsModule, NgClass, TranslatorPipe, TranslateModule]
})
export class Tab6Component {
  @Input() contentForm: NgForm;

  private utilsService = inject(UtilsService);
  protected nodeResolver = inject(NodeResolver);

  updateNode() {
    this.utilsService.update(this.nodeResolver.dataModel).subscribe({});
  }
}

