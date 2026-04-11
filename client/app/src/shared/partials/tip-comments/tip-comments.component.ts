import {AppDataService} from "@app/app-data.service";
import {Component, Input, inject} from "@angular/core";
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
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {AutoExpandDirective} from "@app/shared/directive/auto-expand.directive";
import {PaginatedInterfaceComponent} from "@app/shared/components/paginated-interface/paginated-interface.component";


@Component({
    selector: "src-tip-comments",
    templateUrl: "./tip-comments.component.html",
    standalone: true,
    imports: [AutoExpandDirective, DatePipe, FormsModule, NgbTooltipModule, PaginatedInterfaceComponent, TranslateModule, TranslatorPipe]
})
export class TipCommentsComponent {
  private maskService = inject(MaskService);
  protected preferenceResolver = inject(PreferenceResolver);
  private rTipService = inject(ReceiverTipService);
  protected authenticationService = inject(AuthenticationService);
  protected utilsService = inject(UtilsService);
  appDataService = inject(AppDataService);

  @Input() tipService: ReceiverTipService | WbtipService;
  @Input() key: string;
  @Input() redactMode: boolean;
  @Input() redactOperationTitle: string;

  collapsed = false;
  newCommentContent = "";
  newComments: Comment;

  public toggleCollapse() {
    this.collapsed = !this.collapsed;
  }

  newComment() {
    const response = this.tipService.newComment(this.newCommentContent, this.key);
    this.newCommentContent = "";

    response.subscribe(
      (data) => {
        this.tipService.tip.comments = [data, ...this.tipService.tip.comments];
      }
    );
  }

  getSortedComments(data: Comment[]): Comment[] {
    return data;
  }

  redactInformation(type:string, id:string, entry:string, content:string){
    this.maskService.redactInfo(type,id,entry,content,this.tipService.tip)
  }

  maskContent(id: string, index: string, value: string) {
    return this.maskService.maskingContent(id,index,value,this.tipService.tip)
  }
}
