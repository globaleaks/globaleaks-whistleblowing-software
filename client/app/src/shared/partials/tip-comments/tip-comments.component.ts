import {AppDataService} from "@app/app-data.service";
import {ChangeDetectorRef, Component, Input, OnInit} from "@angular/core";
import {WbtipService} from "@app/services/helper/wbtip.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {ReceiverTipService} from "@app/services/helper/receiver-tip.service";
import {Comment} from "@app/models/app/shared-public-model";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {MaskService} from "@app/shared/services/mask.service";
import { Forwarding } from "@app/models/reciever/reciever-tip-data";

@Component({
  selector: "src-tip-comments",
  templateUrl: "./tip-comments.component.html"
})
export class TipCommentsComponent implements OnInit {
  @Input() tipService: ReceiverTipService | WbtipService;
  @Input() key: string;
  @Input() redactMode: boolean;
  @Input() redactOperationTitle: string;
  @Input() organizations: Forwarding[] = [];

  collapsed = false;
  newCommentContent = "";
  currentCommentsPage: number = 1;
  itemsPerPage = 5;
  comments: Comment[] = [];
  newComments: Comment;

  constructor(private maskService:MaskService,protected preferenceResolver:PreferenceResolver,private rTipService: ReceiverTipService, protected authenticationService: AuthenticationService, protected utilsService: UtilsService, private cdr: ChangeDetectorRef, public appDataService: AppDataService) {

  }

  ngOnInit() {
    this.comments = this.tipService.tip.comments;
  }

  public toggleCollapse() {
    this.collapsed = !this.collapsed;
  }

  newComment() {
    
    const response = this.tipService.newComment(this.newCommentContent, this.key, this.organizations.map(_=>_.tid));
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

    if(this.key === 'oe'){
      data = data.filter(commento => this.organizations.some(org => org.comments?.includes(commento.id)))
    }
    
    return data;
  }

  redactInformation(type:string, id:string, entry:string, content:string){
    this.maskService.redactInfo(type,id,entry,content,this.tipService.tip)
  }

  maskContent(id: string, index: string, value: string) {
    return this.maskService.maskingContent(id,index,value,this.tipService.tip)
  }
}
