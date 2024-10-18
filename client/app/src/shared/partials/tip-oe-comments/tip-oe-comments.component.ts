import { ChangeDetectorRef, Component, Input } from '@angular/core';
import { AppDataService } from '@app/app-data.service';
import { AuthenticationService } from '@app/services/helper/authentication.service';
import { ReceiverTipService } from '@app/services/helper/receiver-tip.service';
import { PreferenceResolver } from '@app/shared/resolvers/preference.resolver';
import { MaskService } from '@app/shared/services/mask.service';
import { UtilsService } from '@app/shared/services/utils.service';
import {Comment} from "@app/models/app/shared-public-model";
import { Forwarding } from '@app/models/reciever/reciever-tip-data';

@Component({
  selector: 'src-tip-oe-comments',
  templateUrl: './tip-oe-comments.component.html'
})
export class TipOeCommentsComponent {
  @Input() tipService: ReceiverTipService ;
  @Input() key: string;
  @Input() redactMode: boolean;
  @Input() redactOperationTitle: string;

  @Input() organizations: Forwarding[];

  collapsed = false;
  newCommentContent = "";
  currentCommentsPage: number = 1;
  itemsPerPage = 5;
  comments: Comment[] = [];
  newComments: Comment;


  constructor(private readonly maskService:MaskService, protected preferenceResolver:PreferenceResolver, protected authenticationService: AuthenticationService, protected utilsService: UtilsService, private readonly cdr: ChangeDetectorRef, public appDataService: AppDataService) {

  }

  ngOnInit() {
    this.comments = this.tipService.tip.comments;

  }

  public toggleCollapse() {
    this.collapsed = !this.collapsed;
  }

  newComment() {
    const response = this.tipService.newComment(this.newCommentContent, this.key, this.organizations.map(_ => _.tid));
    this.newCommentContent = "";

    response.subscribe(
      (data) => {
        this.comments = this.tipService.tip.comments;
        this.tipService.tip.comments.push(data);
        this.comments = [...this.comments, this.newComments];

        this.organizations.forEach(org => org.comments?.push({"id": data.id, "author_type":"main"}))

        if(this.tipService.forwarding){

          if(!this.tipService.forwarding.comments)
            this.tipService.forwarding.comments = [];
          
          this.tipService.forwarding.comments?.push({"id": data.id, "author_type":"main"})
        }

        this.cdr.detectChanges();
      }
    );
  }

  getSortedComments(data: Comment[]): Comment[] {
    data = data.filter(comment => this.organizations.map(_=>_.comments).flat().some(i => i?.id === comment.id))
    return data;
  }

  redactInformation(type:string, id:string, entry:string, content:string){
    this.maskService.redactInfo(type,id,entry,content,this.tipService.tip)
  }

  maskContent(id: string, index: string, value: string) {
    return this.maskService.maskingContent(id,index,value,this.tipService.tip)
  }
}
