import {HttpClient} from "@angular/common/http";
import {Component, EventEmitter, Input, OnInit, Output, inject} from "@angular/core";
import {NgForm, FormsModule} from "@angular/forms";
import {NgbModal, NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {DeleteConfirmationComponent} from "@app/shared/modals/delete-confirmation/delete-confirmation.component";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {QuestionnairesResolver} from "@app/shared/resolvers/questionnaires.resolver";
import {UsersResolver} from "@app/shared/resolvers/users.resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import {Observable} from "rxjs";
import {contextResolverModel} from "@app/models/resolvers/context-resolver-model";
import {questionnaireResolverModel} from "@app/models/resolvers/questionnaire-model";
import {User} from "@app/models/resolvers/user-resolver-model";
import {nodeResolverModel} from "@app/models/resolvers/node-resolver-model";
import {NgClass} from "@angular/common";
import {ImageUploadDirective} from "@app/shared/directive/image-upload.directive";
import {NgSelectComponent, NgOptionTemplateDirective} from "@ng-select/ng-select";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {FilterPipe} from "@app/shared/pipes/filter.pipe";

@Component({
    selector: "src-context-editor",
    templateUrl: "./context-editor.component.html",
    standalone: true,
    imports: [ImageUploadDirective, FormsModule, NgbTooltipModule, NgSelectComponent, NgOptionTemplateDirective, NgClass, TranslatorPipe, FilterPipe]
})
export class ContextEditorComponent implements OnInit {
  private http = inject(HttpClient);
  private modalService = inject(NgbModal);
  protected nodeResolver = inject(NodeResolver);
  private usersResolver = inject(UsersResolver);
  private questionnairesResolver = inject(QuestionnairesResolver);
  private utilsService = inject(UtilsService);

  @Input() contextsData: contextResolverModel[];
  @Input() contextResolver: contextResolverModel;
  @Input() index: number;
  @Input() editContext: NgForm;
  @Output() dataToParent = new EventEmitter<string>();
  editing: boolean = false;
  showAdvancedSettings: boolean = false;
  showSelect: boolean = false;
  questionnairesData: questionnaireResolverModel[] = [];
  usersData: User[] = [];
  nodeData: nodeResolverModel;
  selected = {value: []};
  adminReceiversById: { [userId: string]: User } = {};

  ngOnInit(): void {
    this.questionnairesData = this.questionnairesResolver.dataModel;

    this.usersData = this.usersResolver.dataModel.users;
    this.nodeData = this.nodeResolver.dataModel;
    this.adminReceiversById = this.utilsService.array_to_map(this.usersResolver.dataModel.users);
  }

  toggleEditing(): void {
    this.editing = !this.editing;
  }

  swap($event: Event, index: number, n: number): void {
    $event.stopPropagation();

    const target = index + n;
    if (target < 0 || target >= this.contextsData.length) {
      return;
    }

    [this.contextsData[index], this.contextsData[target]] =
      [this.contextsData[target], this.contextsData[index]];

    this.http.put("api/admin/contexts", {
      operation: "order_elements",
      args: {ids: this.contextsData.map(c => c.id)},
    }).subscribe();
  }

  moveUp(e: Event, idx: number): void {
    this.swap(e, idx, -1);
  }

  moveDown(e: Event, idx: number): void {
    this.swap(e, idx, 1);
  }

  swapReceiver(index: number, n: number): void {
    const target = index + n;
    if (target > -1 && target < this.contextResolver.receivers.length) {
      const tmp = this.contextResolver.receivers[target];
      this.contextResolver.receivers[target] = this.contextResolver.receivers[index];
      this.contextResolver.receivers[index] = tmp;
    }
  }

  receiverNotSelectedFilter(item: User): boolean {
    return this.contextResolver.receivers.indexOf(item.id) === -1;
  }

  moveUpReceiver(index: number): void {
    this.swapReceiver(index, -1);
  }

  moveDownReceiver(index: number): void {
    this.swapReceiver(index, 1);
  }

  toggleSelect(): void {
    this.showSelect = true;
  }

  moveReceiver(rec: User): void {
    if (rec && this.contextResolver.receivers.indexOf(rec.id) === -1) {
      this.contextResolver.receivers.push(rec.id);
      this.showSelect = false;
    }
  }

  deleteContext(context: contextResolverModel): void {
    this.openConfirmableModalDialog(context, "").subscribe();
  }

  openConfirmableModalDialog(arg: contextResolverModel, scope: any): Observable<string> {
    scope = !scope ? this : scope;
    return new Observable((observer) => {
      const modalRef = this.modalService.open(DeleteConfirmationComponent,{backdrop: 'static',keyboard: false});
      modalRef.componentInstance.arg = arg;
      modalRef.componentInstance.scope = scope;
      modalRef.componentInstance.confirmFunction = () => {
        observer.complete()
        return this.utilsService.deleteAdminContext(arg.id).subscribe(_ => {
          this.utilsService.deleteResource(this.contextsData,arg);
        });
      };
    });
  }

  saveContext(context: contextResolverModel) {
    if (context.additional_questionnaire_id === null) {
      context.additional_questionnaire_id = "";
    }
    this.utilsService.updateAdminContext(context, context.id).subscribe(_ => {
    });
  }

}
