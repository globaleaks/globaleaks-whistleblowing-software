import {Component, EventEmitter, Input, Output, inject} from "@angular/core";
import {Answers} from "@app/models/receiver/receiver-tip-data";
import {WbtipService} from "@app/services/helper/wbtip.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {TipFieldComponent} from "../tip-field/tip-field.component";
import {FormsModule} from "@angular/forms";
import {NgFormChangeDirective} from "../../directive/ng-form-change.directive";
import {WhistleblowerIdentityFieldComponent} from "../../../pages/whistleblower/fields/whistleblower-identity-field/whistleblower-identity-field.component";
import {RFilesUploadStatusComponent} from "../rfiles-upload-status/r-files-upload-status.component";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";

@Component({
    selector: "src-whistleblower-identity",
    templateUrl: "./whistleblower-identity.component.html",
    standalone: true,
    imports: [TipFieldComponent, FormsModule, NgbTooltipModule, NgFormChangeDirective, WhistleblowerIdentityFieldComponent, RFilesUploadStatusComponent, TranslateModule, TranslatorPipe]
})
export class WhistleblowerIdentityComponent {
  protected wbTipService = inject(WbtipService);
  protected utilsService = inject(UtilsService);

  @Input() field: any;
  @Input() step: any;
  @Input() answers: Answers;
  @Input() uploadEstimateTime: number;
  @Input() isUploading: boolean | undefined;
  @Input() uploadProgress: number | undefined;

  @Output() provideIdentityInformation = new EventEmitter<{ param1: string, param2: Answers }>();
  @Output() onFormUpdate = new EventEmitter<void>();
  @Output() notifyFileUpload: EventEmitter<any> = new EventEmitter<any>();

  collapsed = false;
  protected readonly JSON = JSON;
  identity_provided: boolean = true;

  constructor() {
    this.collapsed = this.wbTipService.tip.data.whistleblower_identity_provided;
  }

  public toggleCollapse() {
    this.collapsed = !this.collapsed;
  }

  onFormChange() {
    this.onFormUpdate.emit();
  }

  stateChanged(status: boolean) {
    this.identity_provided = status;
  }
}
