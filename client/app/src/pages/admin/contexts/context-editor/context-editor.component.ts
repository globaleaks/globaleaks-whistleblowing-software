import {Component, OnInit, computed, inject, input, output} from "@angular/core";
import {TranslatePipe} from "@ngx-translate/core";
import {NgForm, FormsModule} from "@angular/forms";
import {NgbModal, NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {DeleteConfirmationComponent} from "@app/shared/modals/delete-confirmation/delete-confirmation.component";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {SelectablesResolver} from "@app/shared/resolvers/selectables.resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import {Observable} from "rxjs";
import {contextResolverModel} from "@app/models/resolvers/context-resolver-model";
import {SelectableEntry} from "@app/models/app/selectables";
import {nodeResolverModel} from "@app/models/resolvers/node-resolver-model";
import {ImageUploadDirective} from "@app/shared/directive/image-upload.directive";
import {NgSelectComponent, NgOptionTemplateDirective} from "@ng-select/ng-select";
import {ListItemComponent} from "@app/shared/components/list-item/list-item.component";

@Component({
    selector: "src-context-editor",
    templateUrl: "./context-editor.component.html",
    standalone: true,
    imports: [TranslatePipe, ImageUploadDirective, FormsModule, NgbTooltipModule, NgSelectComponent, NgOptionTemplateDirective, ListItemComponent]
})
export class ContextEditorComponent implements OnInit {
  private modalService = inject(NgbModal);
  protected nodeResolver = inject(NodeResolver);
  private selectablesResolver = inject(SelectablesResolver);
  private utilsService = inject(UtilsService);

  readonly contextsData = input.required<contextResolverModel[]>();
  readonly contextResolver = input.required<contextResolverModel>();
  readonly index = input.required<number>();
  readonly editContext = input.required<NgForm>();
  readonly deleted = output<string>();
  readonly reorder = output<{
    index: number;
    direction: number;
}>();
  editing = false;
  showAdvancedSettings = false;
  showSelect = false;
  readonly questionnairesData = computed(() => this.selectablesResolver.dataModel.questionnaires);

  // The users receive on a channel through the profile they hold: a profile
  // shared among accounts carries them all, the personal profile of an account
  // carries that one alone and is named by it
  readonly profilesData = computed<SelectableEntry[]>(() => this.selectablesResolver.dataModel.user_profiles);
  readonly profilesById = computed<Record<string, SelectableEntry>>(() => this.utilsService.array_to_map(this.profilesData()));
  nodeData: nodeResolverModel;
  selected = {value: []};

  ngOnInit(): void {
    this.nodeData = this.nodeResolver.dataModel;
  }

  moveUp(e: Event, idx: number): void {
    e.stopPropagation();
    this.reorder.emit({ index: idx, direction: -1 });
  }

  moveDown(e: Event, idx: number): void {
    e.stopPropagation();
    this.reorder.emit({ index: idx, direction: 1 });
  }

  profileNotSelectedFilter(item: SelectableEntry): boolean {
    return this.namedProfiles().indexOf(item.id) === -1;
  }

  namedProfiles(): string[] {
    const context = this.contextResolver();

    if (!context.profiles) {
      context.profiles = [];
    }

    return context.profiles;
  }

  toggleSelect(): void {
    this.showSelect = true;
  }

  addProfile(profile: SelectableEntry): void {
    if (profile && this.namedProfiles().indexOf(profile.id) === -1) {
      this.namedProfiles().push(profile.id);
      this.showSelect = false;
    }
  }

  removeProfile(index: number): void {
    this.namedProfiles().splice(index, 1);
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
        return this.utilsService.deleteAdminContext(arg.id).subscribe(() => {
	  this.deleted.emit(arg.id);
        });
      };
    });
  }

  saveContext(context: contextResolverModel) {
    if (context.additional_questionnaire_id === null) {
      context.additional_questionnaire_id = "";
    }
    this.utilsService.updateAdminContext(context, context.id).subscribe(updatedContext => {
      Object.assign(context, updatedContext);
    });
  }

}
