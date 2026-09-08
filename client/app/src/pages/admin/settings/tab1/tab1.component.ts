import {Component, inject, input} from "@angular/core";
import {ControlContainer, NgForm, FormsModule} from "@angular/forms";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {AppConfigService} from "@app/services/root/app-config.service";
import {Constants} from "@app/shared/constants/constants";
import {AppDataService} from "@app/app-data.service";
import {ImageUploadDirective} from "@app/shared/directive/image-upload.directive";
import {TranslateModule} from "@ngx-translate/core";
import {HeldByProfileDirective} from "@app/shared/directive/held-by-profile.directive";

@Component({
    selector: "src-tab1",
    templateUrl: "./tab1.component.html",
    viewProviders: [{ provide: ControlContainer, useExisting: NgForm }],
    standalone: true,
    imports: [
    HeldByProfileDirective,
    ImageUploadDirective,
    FormsModule,
    TranslateModule
],
})
export class Tab1Component {
  private readonly appConfigService = inject(AppConfigService);
  protected nodeResolver = inject(NodeResolver);
  protected appDataService = inject(AppDataService);
  protected authenticationService = inject(AuthenticationService);
  private readonly utilsService = inject(UtilsService);

  protected readonly Constants = Constants;
  readonly contentForm = input.required<NgForm>();

  updateNode() {
    this.utilsService.update(this.nodeResolver.dataModel).subscribe((node) => {
      // A save is what makes a site start holding a value of its own, and the command to give it
      // up must be there the moment it does. The answer says what the site holds now: the strips
      // read it from there, without waiting for the navigation below to bring it again.
      this.nodeResolver.patch({held_keys: node.held_keys});
      this.appConfigService.reinit();
      this.utilsService.reloadComponent();
    });
  }
}