import {Component, ElementRef, OnInit, computed, inject, input, output} from "@angular/core";
import {TranslatePipe} from "@ngx-translate/core";
import {NgForm, FormsModule} from "@angular/forms";
import {NgbModal, NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {DeleteConfirmationComponent} from "@app/shared/modals/delete-confirmation/delete-confirmation.component";
import {AuthenticationService} from "@app/services/helper/authentication.service";
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
import {SelectionEditorComponent, SelectionEntry} from "@app/shared/components/selection-editor/selection-editor.component";
import {exchangeType, exchangeTypeLabels} from "@app/models/admin/exchange";

@Component({
    selector: "src-context-editor",
    templateUrl: "./context-editor.component.html",
    standalone: true,
    imports: [TranslatePipe, ImageUploadDirective, FormsModule, NgbTooltipModule, NgSelectComponent, NgOptionTemplateDirective, ListItemComponent, SelectionEditorComponent]
})
export class ContextEditorComponent implements OnInit {
  private modalService = inject(NgbModal);
  private elementRef = inject(ElementRef);
  private authenticationService = inject(AuthenticationService);
  protected nodeResolver = inject(NodeResolver);
  private selectablesResolver = inject(SelectablesResolver);
  private utilsService = inject(UtilsService);

  readonly contextsData = input.required<contextResolverModel[]>();
  readonly contextResolver = input.required<contextResolverModel>();
  readonly index = input.required<number>();
  readonly editContext = input.required<NgForm>();
  // A link pointing at this channel opens its card and brings it into view
  readonly expanded = input(false);
  readonly deleted = output<string>();
  readonly reorder = output<{
    index: number;
    direction: number;
}>();
  editing = false;
  showAdvancedSettings = false;
  showSelect = false;

  /**
   * A channel of the exchanges receives what the other sites of the platform
   * file on this one: it carries the name the exchanges are known by on this
   * side, the recipients that take part in them, the questionnaire composing
   * what lives here and how long it lasts, while what a channel configures
   * for the reporting people has no part in it, since they neither reach it
   * nor are offered it.
   */
  isExchangeChannel(): boolean {
    return !!this.contextResolver().exchange;
  }

  // The kinds of exchange running through the channel, in a word
  exchangeTypes(): string[] {
    return this.contextResolver().exchange_types || [];
  }

  exchangeTypeLabel(type: string): string {
    return exchangeTypeLabels[type as exchangeType] || type;
  }

  /**
   * A channel of the exchanges is configured by the administrators of the
   * platform, that established the exchanges running through it and enter the
   * site holding it to configure it. The administrators of the site read it
   * where it lives but do not write it.
   */
  canConfigure(): boolean {
    return !this.isExchangeChannel() ||
           this.nodeResolver.dataModel.root_tenant ||
           !!this.authenticationService.session.properties.management_session;
  }

  readonly questionnairesData = computed(() => this.selectablesResolver.dataModel.questionnaires);

  // Users receive through their profile: a shared one carries all its accounts, a personal one its
  // account
  readonly profilesData = computed<SelectableEntry[]>(() => this.selectablesResolver.dataModel.user_profiles);
  readonly profilesById = computed<Record<string, SelectableEntry>>(() => this.utilsService.array_to_map(this.profilesData()));
  nodeData: nodeResolverModel;
  selected = {value: []};

  ngOnInit(): void {
    this.nodeData = this.nodeResolver.dataModel;

    if (this.expanded()) {
      this.editing = true;
      // The card is reached from elsewhere: it is brought into view once the
      // list holding it has been laid out
      setTimeout(() => this.elementRef.nativeElement.scrollIntoView({behavior: "smooth", block: "start"}));
    }
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

  /**
   * A channel names the additional questionnaires it can ask of its reports,
   * and elects one of them as the automatic one: the elected questionnaire is
   * asked of every report filed on the channel by the channel itself, while
   * the others are asked of a single report by its recipients. A channel that
   * elects none asks nothing by itself and leaves the whole decision to them.
   */
  namedAdditionalQuestionnaires(): string[] {
    const context = this.contextResolver();

    if (!context.additional_questionnaires) {
      context.additional_questionnaires = [];
    }

    return context.additional_questionnaires;
  }

  additionalQuestionnaires(): SelectionEntry[] {
    const questionnaires = this.utilsService.array_to_map(this.questionnairesData());

    return this.namedAdditionalQuestionnaires()
               .map(id => ({id: id, label: questionnaires[id] ? questionnaires[id].name : id}));
  }

  // The questionnaire composing the reports of the channel is not among the
  // ones it can additionally ask: it is already asked of every one of them
  additionalQuestionnaireOptions(): SelectionEntry[] {
    const named = this.namedAdditionalQuestionnaires();

    return this.questionnairesData()
               .filter(item => item.id !== this.contextResolver().questionnaire_id && named.indexOf(item.id) === -1)
               .map(item => ({id: item.id, label: item.name}));
  }

  addAdditionalQuestionnaire(id: string): void {
    if (id && this.namedAdditionalQuestionnaires().indexOf(id) === -1) {
      this.namedAdditionalQuestionnaires().push(id);
    }
  }

  removeAdditionalQuestionnaire(index: number): void {
    this.namedAdditionalQuestionnaires().splice(index, 1);
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
    this.utilsService.updateAdminContext(context, context.id).subscribe(updatedContext => {
      Object.assign(context, updatedContext);
    });
  }

}
