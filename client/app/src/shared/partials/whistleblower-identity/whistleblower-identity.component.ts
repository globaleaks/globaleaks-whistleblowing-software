import {CollapsiblePanelComponent} from "@app/shared/components/collapsible-panel/collapsible-panel.component";
import {Component, inject, input, output} from "@angular/core";
import {Answers} from "@app/models/receiver/receiver-tip-data";
import {WbtipService} from "@app/services/helper/wbtip.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {TipFieldComponent} from "../tip-field/tip-field.component";
import {FormsModule} from "@angular/forms";
import {NgFormChangeDirective} from "../../directive/ng-form-change.directive";
import {WhistleblowerIdentityFieldComponent} from "@app/pages/whistleblower/fields/whistleblower-identity-field/whistleblower-identity-field.component";
import {RFilesUploadStatusComponent} from "../rfiles-upload-status/r-files-upload-status.component";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-whistleblower-identity",
    templateUrl: "./whistleblower-identity.component.html",
    standalone: true,
    imports: [CollapsiblePanelComponent, TipFieldComponent, FormsModule, NgbTooltipModule, NgFormChangeDirective, WhistleblowerIdentityFieldComponent, RFilesUploadStatusComponent, TranslateModule]
})
export class WhistleblowerIdentityComponent {
  protected wbTipService = inject(WbtipService);
  protected utilsService = inject(UtilsService);

  readonly submission = input<any>();
  readonly field = input<any>();
  readonly step = input<any>();
  readonly answers = input.required<Answers>();
  readonly uploadEstimateTime = input<number>();
  readonly isUploading = input<boolean>();
  readonly uploadProgress = input<number>();

  readonly provideIdentityInformation = output<{
    param1: string;
    param2: Answers;
}>();
  readonly formUpdate = output<void>();
  readonly notifyFileUpload = output<any>();
  readonly uploads = input<Record<string, any>>();

  fileUploadUrl = "api/whistleblower/wbtip/wbfiles";

  collapsed = false;
  protected readonly JSON = JSON;
  identity_provided = false;

  constructor() {
    this.collapsed = this.wbTipService.tip.data.whistleblower_identity_provided;
  }

  public toggleCollapse() {
    this.collapsed = !this.collapsed;
  }

  onFormChange() {
    this.formUpdate.emit();
  }

  stateChanged(status: boolean) {
    this.identity_provided = status;
    this.submission().submission.identity_provided = status;
  }
}
