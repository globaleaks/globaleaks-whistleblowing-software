import {AppDataService} from "@app/app-data.service";
import {ChangeDetectorRef, Component, Input, OnInit, inject} from "@angular/core";
import {WbtipService} from "@app/services/helper/wbtip.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {ReceiverTipService} from "@app/services/helper/receiver-tip.service";
import {Comment} from "@app/models/app/shared-public-model";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {MaskService} from "@app/shared/services/mask.service";
import {SlicePipe, DatePipe} from "@angular/common";
import {FormsModule} from "@angular/forms";
import {NgbPagination, NgbPaginationFirst, NgbPaginationPrevious, NgbPaginationNext, NgbPaginationLast, NgbTooltipModule, NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {OrderByPipe} from "@app/shared/pipes/order-by.pipe";
import {FilterPipe} from "@app/shared/pipes/filter.pipe";
import {AutoExpandDirective} from "@app/shared/directive/auto-expand.directive";
import {FileInfoComponent} from "@app/shared/modals/file-info/file-info.component";

@Component({
    selector: "src-tip-comments",
    templateUrl: "./tip-comments.component.html",
    standalone: true,
    imports: [AutoExpandDirective, FormsModule, NgbPagination, NgbPaginationFirst, NgbPaginationPrevious, NgbPaginationNext, NgbPaginationLast, NgbTooltipModule, SlicePipe, DatePipe, TranslateModule, TranslatorPipe, OrderByPipe, FilterPipe]
})
export class TipCommentsComponent implements OnInit {
  private maskService = inject(MaskService);
  protected preferenceResolver = inject(PreferenceResolver);
  private rTipService = inject(ReceiverTipService);
  protected authenticationService = inject(AuthenticationService);
  protected utilsService = inject(UtilsService);
  private cdr = inject(ChangeDetectorRef);
  appDataService = inject(AppDataService);
  private modalService = inject(NgbModal);

  @Input() tipService: ReceiverTipService | WbtipService;
  @Input() key: string;
  @Input() redactMode: boolean;
  @Input() redactOperationTitle: string;

  collapsed = false;
  newCommentContent = "";
  currentCommentsPage = 1;
  itemsPerPage = 5;
  comments: Comment[] = [];
  newComments: Comment;

  ngOnInit() {
    this.comments = this.tipService.tip.comments;
  }

  public toggleCollapse() {
    this.collapsed = !this.collapsed;
  }

  newComment() {
    const response = this.tipService.newComment(this.newCommentContent, this.key);
    this.newCommentContent = "";

    response.subscribe(
      (data) => {
        this.comments = this.tipService.tip.comments;
        this.tipService.tip.comments.push(data);
        this.comments = [...this.comments, this.newComments];
        this.cdr.detectChanges();
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

  openCommentInfo(comment: Comment) {
    const modalRef = this.modalService.open(FileInfoComponent);
    // Create a file-like object from the comment for the modal
    modalRef.componentInstance.file = {
      name: 'Comment',
      type: 'text/plain',
      size: comment.content ? comment.content.length : 0,
      creation_date: comment.creation_date,
      hash_sha256: comment.hash_sha256,
      hash_sha512: comment.hash_sha512,
      description: ''
    };
    modalRef.componentInstance.receivers_by_id = this.tipService.tip.receivers_by_id;
  }
}
