import {CollapsiblePanelComponent} from "@app/shared/components/collapsible-panel/collapsible-panel.component";
import {AppDataService} from "@app/app-data.service";
import {Component, inject, input} from "@angular/core";
import {WbtipService} from "@app/services/helper/wbtip.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {ReceiverTipService} from "@app/services/helper/receiver-tip.service";
import {Comment} from "@app/models/app/shared-public-model";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {MaskService} from "@app/shared/services/mask.service";
import {DatePipe} from "@angular/common";
import {FormsModule} from "@angular/forms";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {TranslateModule} from "@ngx-translate/core";
import {AutoExpandDirective} from "@app/shared/directive/auto-expand.directive";
import {PaginatedInterfaceComponent} from "@app/shared/components/paginated-interface/paginated-interface.component";


@Component({
    selector: "src-tip-comments",
    templateUrl: "./tip-comments.component.html",
    standalone: true,
    imports: [CollapsiblePanelComponent, AutoExpandDirective, DatePipe, FormsModule, NgbTooltipModule, PaginatedInterfaceComponent, TranslateModule]
})
export class TipCommentsComponent {
  private maskService = inject(MaskService);
  protected preferenceResolver = inject(PreferenceResolver);
  private rTipService = inject(ReceiverTipService);
  protected authenticationService = inject(AuthenticationService);
  protected utilsService = inject(UtilsService);
  appDataService = inject(AppDataService);

  readonly tipService = input.required<ReceiverTipService | WbtipService>();
  readonly key = input.required<string>();
  readonly redactMode = input<boolean>();
  readonly redactOperationTitle = input<string>();

  collapsed = false;
  newCommentContent = "";
  newComments: Comment;

  public toggleCollapse() {
    this.collapsed = !this.collapsed;
  }

  newComment() {
    const response = this.tipService().newComment(this.newCommentContent, this.key());
    this.newCommentContent = "";

    response.subscribe(
      (data) => {
        this.tipService().tip.comments = [data, ...this.tipService().tip.comments];
      }
    );
  }

  getSortedComments(data: Comment[]): Comment[] {
    return data;
  }

  redactInformation(type:string, id:string, entry:string, content:string){
    this.maskService.redactInfo(type,id,entry,content,this.tipService().tip)
  }

  maskContent(id: string, index: string, value: string) {
    // The masker reads the real content; the masked rendering is shown to
    // them only while editing the masking (redact mode).
    if (!this.redactMode() &&
        (this.preferenceResolver.dataModel?.profile?.permissions?.can_mask_information ||
         this.preferenceResolver.dataModel?.profile?.permissions?.can_redact_information)) {
      return value;
    }

    return this.maskService.maskingContent(id, index, value, this.tipService().tip);
  }

  isCommentRead(comment: Comment): boolean {
    if (this.tipService instanceof ReceiverTipService) {
      if (!comment.author_id) {
        return new Date(this.tipService.tip.last_access) > new Date(comment.creation_date);
      } else {
        return new Date(this.tipService.tip.itip_last_access) > new Date(comment.creation_date);
      }
    } else if (this.tipService instanceof WbtipService) {
      if (!comment.author_id) {
        return this.tipService.tip.receivers.some(r => r.last_access && new Date(r.last_access) > new Date(comment.creation_date));
      } else {
        return new Date(this.tipService.tip.last_access) > new Date(comment.creation_date);
      }
    }
    return false;
  }
}
