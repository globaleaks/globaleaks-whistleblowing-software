import {CollapsiblePanelComponent} from "@app/shared/components/collapsible-panel/collapsible-panel.component";
import {AppDataService} from "@app/app-data.service";
import {Component, inject, input} from "@angular/core";
import {WbtipService} from "@app/services/helper/wbtip.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {ReceiverTipService} from "@app/services/helper/receiver-tip.service";
import {Comment} from "@app/models/app/shared-public-model";
import {ForwardingChannel} from "@app/models/receiver/receiver-tip-data";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {MaskService} from "@app/shared/services/mask.service";
import {DatePipe} from "@angular/common";
import {FormsModule} from "@angular/forms";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {TranslateModule} from "@ngx-translate/core";
import {AutoExpandDirective} from "@app/shared/directive/auto-expand.directive";
import {PaginatedInterfaceComponent} from "@app/shared/components/paginated-interface/paginated-interface.component";
import {RecieverTipData} from "@app/models/receiver/receiver-tip-data";


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
  readonly key = input('');
  readonly redactMode = input<boolean>();
  readonly redactOperationTitle = input<string>();

  // A comments source other than the tip's own, presented with the very same
  // interface; pairs with readOnly on spaces the viewer cannot write into
  readonly comments = input<Comment[] | null>(null);
  readonly readOnly = input(false);

  collapsed = false;
  newCommentContent = "";
  newComments: Comment;

  public toggleCollapse() {
    this.collapsed = !this.collapsed;
  }

  get commentList(): Comment[] {
    return this.comments() || this.tipService().tip.comments;
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

  getCommentAuthorName(comment: Comment): string {
    if (comment.author_name) {
      return comment.author_name;
    }

    if (comment.author_id === this.preferenceResolver.dataModel.id) {
      return this.preferenceResolver.dataModel.name;
    }

    const author = this.tipService().tip.receivers_by_id[comment.author_id];
    if (author) {
      return author.name;
    }

    // On the report created by a forward each tenant is serialized its own
    // recipients alone: an author that is not among them writes from the
    // other side of the forward and is presented by the name of its tenant
    const forwarding = (this.tipService().tip as {forwarding?: ForwardingChannel}).forwarding;
    if (comment.author_id && forwarding) {
      return forwarding.internaltip_id ? forwarding.to_tenant_name : forwarding.from_tenant_name;
    }

    return "Recipient";
  }

  isCommentRead(comment: Comment): boolean {
    if (this.tipService() instanceof ReceiverTipService) {
      const tip = this.tipService().tip as RecieverTipData;

      // The space the two tenants of a forward share: a comment of the
      // viewer's side is read once the other side accessed after it, one of
      // the other side once the viewer did
      if (comment.visibility === 'forward') {
        if (comment.author_id && !tip.receivers_by_id[comment.author_id]) {
          return new Date(tip.last_access) > new Date(comment.creation_date);
        }

        return new Date(tip.counterpart_last_access) > new Date(comment.creation_date);
      }

      if (!comment.author_id) {
        return new Date(tip.last_access) > new Date(comment.creation_date);
      } else {
        return new Date(tip.itip_last_access) > new Date(comment.creation_date);
      }
    } else if (this.tipService() instanceof WbtipService) {
      if (!comment.author_id) {
        return this.tipService().tip.receivers.some(r => r.last_access && new Date(r.last_access) > new Date(comment.creation_date));
      } else {
        return new Date(this.tipService().tip.last_access) > new Date(comment.creation_date);
      }
    }
    return false;
  }
}
