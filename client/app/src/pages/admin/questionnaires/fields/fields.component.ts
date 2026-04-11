import {Component, EventEmitter, Input, OnInit, Output, inject} from "@angular/core";
import {NgForm, FormsModule} from "@angular/forms";
import {NgbModal, NgbInputDatepicker, NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {AddOptionHintComponent} from "@app/shared/modals/add-option-hint/add-option-hint.component";
import {AssignScorePointsComponent} from "@app/shared/modals/assign-score-points/assign-score-points.component";
import {DeleteConfirmationComponent} from "@app/shared/modals/delete-confirmation/delete-confirmation.component";
import {TriggerReceiverComponent} from "@app/shared/modals/trigger-receiver/trigger-receiver.component";
import {FieldTemplatesResolver} from "@app/shared/resolvers/field-templates-resolver.service";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {FieldUtilitiesService} from "@app/shared/services/field-utilities.service";
import {HttpService} from "@app/shared/services/http.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {map, Observable, of} from "rxjs";
import {Step, questionnaireResolverModel} from "@app/models/resolvers/questionnaire-model";
import {ParsedFields} from "@app/models/component-model/parsedFields";
import {Field, fieldtemplatesResolverModel} from "@app/models/resolvers/field-template-model";
import {Children, Option, TriggeredByOption} from "@app/models/app/shared-public-model";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {NgClass, DatePipe} from "@angular/common";
import {AddFieldComponent} from "../add-field/add-field.component";
import {AddFieldFromTemplateComponent} from "../add-field-from-template/add-field-from-template.component";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {OrderByPipe} from "@app/shared/pipes/order-by.pipe";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-fields",
    templateUrl: "./fields.component.html",
    standalone: true,
    imports: [FormsModule, NgbInputDatepicker, NgbTooltipModule, NgClass, AddFieldComponent, AddFieldFromTemplateComponent, DatePipe, TranslatorPipe, OrderByPipe, TranslateModule]
})
export class FieldsComponent implements OnInit {
  private authenticationService = inject(AuthenticationService);
  private modalService = inject(NgbModal);
  nodeResolver = inject(NodeResolver);
  private httpService = inject(HttpService);
  private utilsService = inject(UtilsService);
  private fieldTemplates = inject(FieldTemplatesResolver);
  private fieldUtilities = inject(FieldUtilitiesService);

  @Input() editField: NgForm;
  @Input() field: Children | Step | Field;
  @Input() fields: Children[] | Field[] | Step[];
  @Input() type: string;
  @Input() step: Step;
  @Input() parsedFields: ParsedFields;
  @Output() deleted = new EventEmitter<string>();
  custom = "custom";
  editing = false;
  openMinDate = false;
  openMaxDate = false;
  showAddTrigger = false;
  showAddQuestionFromTemplate = false;
  showAddQuestion = false;
  fieldIsMarkableSubjectToStats: boolean;
  fieldIsMarkableSubjectToPreview: boolean;
  fieldTemplatesData: fieldtemplatesResolverModel[];
  children: Children[] | Step[] | Field[];
  new_trigger: { field: string; option: string; sufficient: boolean } = {
    field: "",
    option: "",
    sufficient: false,
  };
  instance: string;

  ngOnInit(): void {
    if (Array.isArray(this.fieldTemplates.dataModel)) {
      this.fieldTemplatesData = this.fieldTemplates.dataModel;
    } else {
      this.fieldTemplatesData = [this.fieldTemplates.dataModel];
    }
    this.fieldIsMarkableSubjectToStats = this.isMarkableSubjectToStats(this.field);
    this.fieldIsMarkableSubjectToPreview = this.isMarkableSubjectToPreview(this.field);
    this.children = this.field.children;
  }

  saveField(field: Step | Field, editing?:boolean) {
    this.utilsService.assignUniqueOrderIndex(field.options);
    return this.httpService.requestUpdateAdminQuestionnaireField(field.id, field).subscribe();
  }

  minDateFormat(value: { year: number; month: number; day: number } | string): string {
    if (typeof (value) !== "string") {
      return `${value.year}-${value.month}-${value.day}`;
    } else {
      return value;
    }
  }

  maxDateFormat(value: { year: number; month: number; day: number } | string): string {
    if (typeof (value) !== "string") {
      return `${value.year}-${value.month}-${value.day}`;
    } else {
      return value;
    }
  }

  toggleEditing() {
    this.editing = !this.editing;
  }

  exportQuestion(field: Step | Field) {
    this.utilsService.saveAs(this.authenticationService,field.label + ".json","api/admin/fieldtemplates/" + field.id + "?multilang=1");
  }

  delField(field: Step | Field) {
    this.openConfirmableModalDialog(field, "").subscribe();
  }

  openConfirmableModalDialog(arg: Step | Field, scope: any): Observable<string> {
    return new Observable((observer) => {
      const modalRef = this.modalService.open(DeleteConfirmationComponent, {backdrop: 'static', keyboard: false});
      modalRef.componentInstance.arg = arg;
      modalRef.componentInstance.scope = scope;

      modalRef.componentInstance.confirmFunction = () => {
        return this.httpService.requestDeleteAdminQuestionareField(arg.id).subscribe(() => {
          this.deleted.emit(this.field.id);
        });
      };
    });
  }

  moveUpAndSave(field: Step | Field): void {
    this.utilsService.moveUp(field);
    this.saveField(field);
  }

  moveDownAndSave(field: Step | Field): void {
    this.utilsService.moveDown(field);
    this.saveField(field);
  }

  moveLeftAndSave(field: Step | Field): void {
    this.utilsService.moveLeft(field);
    this.saveField(field);
  }

  moveRightAndSave(field: Step | Field): void {
    this.utilsService.moveRight(field);
    this.saveField(field);
  }

  typeSwitch(type: string): string {
    if (["inputbox", "textarea"].indexOf(type) !== -1) {
      return "inputbox_or_textarea";
    }

    if (["checkbox", "selectbox"].indexOf(type) !== -1) {
      return "checkbox_or_selectbox";
    }

    return type;
  }

  isMarkableSubjectToStats(field: Step | Field): boolean {
    return ["inputbox", "textarea", "fieldgroup"].indexOf(field.type) === -1;
  }

  isMarkableSubjectToPreview(field: Step | Field): boolean {
    return ["fieldgroup", "fileupload"].indexOf(field.type) === -1;
  }

  toggleMinDate() {
    this.openMinDate = !this.openMinDate;
  }

  toggleMaxDate() {
    this.openMaxDate = !this.openMaxDate;
  }

  toggleAddTrigger() {
    this.showAddTrigger = !this.showAddTrigger;
  };

  delTrigger(trigger: TriggeredByOption): void {
    const index = this.field.triggered_by_options.indexOf(trigger);
    if (index !== -1) {
      this.field.triggered_by_options.splice(index, 1);
    }
  }

  addTrigger() {
    this.field.triggered_by_options.push(this.new_trigger);
    this.toggleAddTrigger();
    this.new_trigger = {"field": "", "option": "", "sufficient": false};
  }

  showOptions(field: Step | Field): boolean {
    if (field.instance === "reference") {
      return false;
    }

    return ["checkbox", "selectbox", "multichoice"].indexOf(field.type) > -1;
  }

  addOption(): void {
    const new_option = {
      id: "",
      label: "",
      hint1: "",
      hint2: "",
      block_submission: false,
      score_points: 0,
      score_type: "none",
      trigger_receiver: [],
      order: 0,
    };

    new_option.order = this.utilsService.newItemOrder(this.field.options, "order");

    this.field.options.push(new_option);
  }

  delOption(option: Option): void {
    const index = this.field.options.indexOf(option);
    if (index !== -1) {
      this.field.options.splice(index, 1);
    }
  }

  moveOptionUp(idx: number): void {
    this.swapOption(idx, -1);
  }

  moveOptionDown(idx: number): void {
    this.swapOption(idx, 1);
  }

  addOptionHintDialog(option: Option) {
    this.openOptionHintDialog(option).subscribe();

  }

  openOptionHintDialog(arg: Option): Observable<string> {
    return new Observable((observer) => {
      const modalRef = this.modalService.open(AddOptionHintComponent, {backdrop: 'static', keyboard: false});
      modalRef.componentInstance.arg = arg;

      modalRef.componentInstance.confirmFunction = () => {
        observer.complete()
      };
    });
  }

  private swapOption(index: number, n: number): void {
    const target = index + n;
    if (target < 0 || target >= this.field.options.length) {
      return;
    }

    const tmp = this.field.options[target];

    this.field.options[target] = this.field.options[index];
    this.field.options[target].order = target;

    this.field.options[index] = tmp;
    this.field.options[index].order = index;
  }

  flipBlockSubmission(option: Option): void {
    option.block_submission = !option.block_submission;
  }

  triggerReceiverDialog(option: Option): void {
    this.openTriggerReceiverDialog(option).subscribe();

  }

  openTriggerReceiverDialog(arg: Option): Observable<string> {
    return new Observable((observer) => {
      const modalRef = this.modalService.open(TriggerReceiverComponent, {backdrop: 'static', keyboard: false});
      modalRef.componentInstance.arg = arg;

      modalRef.componentInstance.confirmFunction = () => {
        observer.complete()
      };
    });
  }

  assignScorePointsDialog(option: Option) {
    this.openAssignScorePointsDialog(option).subscribe();
  }

  openAssignScorePointsDialog(arg: Option): Observable<string> {
    return new Observable((observer) => {
      const modalRef = this.modalService.open(AssignScorePointsComponent, {backdrop: 'static', keyboard: false});
      modalRef.componentInstance.arg = arg;

      modalRef.componentInstance.confirmFunction = () => {
        observer.complete()
      };
    });
  }

  toggleAddQuestionFromTemplate() {
    this.showAddQuestionFromTemplate = !this.showAddQuestionFromTemplate;
    this.showAddQuestion = false;
  }

  toggleAddQuestion() {
    this.showAddQuestion = !this.showAddQuestion;
    this.showAddQuestionFromTemplate = false;
  }

  isCustomValidation(field: Step | Field): boolean {
    return field?.attrs?.input_validation?.value === 'custom';
  }
}
