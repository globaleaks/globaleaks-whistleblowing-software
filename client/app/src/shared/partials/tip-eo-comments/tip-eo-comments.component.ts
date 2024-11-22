import { ChangeDetectorRef, Component, EventEmitter, Input, Output } from '@angular/core';
import { AppDataService } from '@app/app-data.service';
import { AuthenticationService } from '@app/services/helper/authentication.service';
import { ReceiverTipService } from '@app/services/helper/receiver-tip.service';
import { PreferenceResolver } from '@app/shared/resolvers/preference.resolver';
import { MaskService } from '@app/shared/services/mask.service';
import { UtilsService } from '@app/shared/services/utils.service';
import {Comment} from "@app/models/app/shared-public-model";
import { Forwarding } from '@app/models/reciever/reciever-tip-data';

@Component({
  selector: 'src-tip-eo-comments',
  templateUrl: './tip-eo-comments.component.html'
})
export class TipEoCommentsComponent {
  @Input() tipService: ReceiverTipService ;
  @Input() key: string;
  @Input() redactMode: boolean;
  @Input() redactOperationTitle: string;

  @Input() organizations: Forwarding[];

  @Input() tids: number[];
  @Input() authorType: string = "main";

  @Output() commentAdded = new EventEmitter<void>();

  collapsed = false;
  newCommentContent = "";
  currentCommentsPage: number = 1;
  itemsPerPage = 5;
  comments: Comment[] = [];
  newComments: Comment;


  constructor(private readonly maskService:MaskService, protected preferenceResolver:PreferenceResolver, protected authenticationService: AuthenticationService, protected utilsService: UtilsService, private readonly cdr: ChangeDetectorRef, public appDataService: AppDataService) {

  }

  ngOnInit() {

    
    this.comments = this.tipService.tip.comments.map(comment => {

      this.tipService.tip.forwardings.forEach(forw => {
        if(forw.comments?.some(i => i.id === comment.id)){
          let eo_name = forw.name;
          comment = {
            ...comment,
            eo_name: eo_name
          }
        }

      })

      return comment;
      
    });

    
  }

  public toggleCollapse() {
    this.collapsed = !this.collapsed;
  }

  private getTids() : number[]{
    if (this.tids && this.tids.length > 0) {
      return this.tids;
    }
    
    return this.organizations? this.organizations.filter(org => org.state !== 'closed').map(_ =>  _.tid) : []
  }

  newComment() {

    let tidsToForw = this.getTids();

    const response = this.tipService.newComment(this.newCommentContent, this.key, tidsToForw);
    this.newCommentContent = "";

    response.subscribe(
      (data) => {
        this.tipService.tip.comments.push(data);
        this.comments = this.tipService.tip.comments;

        this.organizations.filter(org => org.state !== 'closed').forEach(org => org.comments?.push({"id": data.id, "author_type": this.authorType}))

        if(this.tipService.forwarding){

          if(!this.tipService.forwarding.comments)
            this.tipService.forwarding.comments = [];
          
          this.tipService.forwarding.comments?.push({"id": data.id, "author_type": this.authorType})
        }

        this.commentAdded.emit();
        this.cdr.detectChanges();
      }
    );
  }

  getSortedComments(data: Comment[]): Comment[] {
    if(this.organizations){
      
      data = data.filter(comment => this.organizations.map(_=>_.comments).flat().some(i => i?.id === comment.id))
      
      
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
