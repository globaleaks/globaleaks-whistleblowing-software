import { Component, Input, inject } from "@angular/core";
import { ControlContainer, NgForm, FormsModule } from "@angular/forms";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {AppConfigService} from "@app/services/root/app-config.service";
import {Constants} from "@app/shared/constants/constants";
import {AppDataService} from "@app/app-data.service";
import { ImageUploadDirective } from "../../../../shared/directive/image-upload.directive";
import { NgClass } from "@angular/common";
import { TranslateModule } from "@ngx-translate/core";
import { TranslatorPipe } from "@app/shared/pipes/translate";

@Component({
    selector: "src-tab1",
    templateUrl: "./tab1.component.html",
    viewProviders: [{ provide: ControlContainer, useExisting: NgForm }],
    standalone: true,
    imports: [
    ImageUploadDirective,
    FormsModule,
    NgClass,
    TranslateModule,
    TranslatorPipe
],
})
export class Tab1Component {
  private appConfigService = inject(AppConfigService);
  protected nodeResolver = inject(NodeResolver);
  protected appDataService = inject(AppDataService);
  protected authenticationService = inject(AuthenticationService);
  private utilsService = inject(UtilsService);

  protected readonly Constants = Constants;
  @Input() contentForm: NgForm;

  updateNode() {
    this.utilsService.update(this.nodeResolver.dataModel).subscribe(_ => {
      this.appConfigService.reinit(false);
      this.utilsService.reloadComponent();
    });
  }
}