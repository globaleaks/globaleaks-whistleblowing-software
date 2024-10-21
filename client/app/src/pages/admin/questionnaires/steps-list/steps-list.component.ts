import { Component, Input, OnInit, inject } from "@angular/core";
import {DeleteConfirmationComponent} from "@app/shared/modals/delete-confirmation/delete-confirmation.component";
import {UtilsService} from "@app/shared/services/utils.service";
import {NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {FieldUtilitiesService} from "@app/shared/services/field-utilities.service";
import {HttpService} from "@app/shared/services/http.service";
import {QuestionnaireService} from "@app/pages/admin/questionnaires/questionnaire.service";
import {Observable} from "rxjs";
import {Step, questionnaireResolverModel} from "@app/models/resolvers/questionnaire-model";
import {ParsedFields} from "@app/models/component-model/parsedFields";
import {TriggeredByOption} from "@app/models/app/shared-public-model";

import { FormsModule } from "@angular/forms";
import { StepComponent } from "../step/step.component";
import { TranslatorPipe } from "@app/shared/pipes/translate";
import { TranslateModule } from "@ngx-translate/core";

@Component({
    selector: "src-steps-list",
    templateUrl: "./steps-list.component.html",
    standalone: true,
    imports: [FormsModule, StepComponent, TranslatorPipe, TranslateModule]
})
export class StepsListComponent implements OnInit {
  private utilsService = inject(UtilsService);
  private questionnaireService = inject(QuestionnaireService);
  private modalService = inject(NgbModal);
  private fieldUtilities = inject(FieldUtilitiesService);
  protected nodeResolver = inject(NodeResolver);
  private httpService = inject(HttpService);

  @Input() step: Step;
  @Input() steps: Step[];
  @Input() questionnaire: questionnaireResolverModel;
  @Input() index: number;
  editing: boolean = false;
  showAddTrigger: boolean = false;
  parsedFields: ParsedFields;
  new_trigger: { field: string; option: string; sufficient: boolean } = {
    field: "",
    option: "",
    sufficient: true,
  };

  ngOnInit(): void {
    this.parsedFields = this.fieldUtilities.parseQuestionnaire(this.questionnaire, {
      fields: [],
      fields_by_id: {},
      options_by_id: {}
    });
  }

  swap($event: Event, index: number, n: number): void {
    this.utilsService.swap($event, index, n, this.questionnaire)
  }

  moveUp(e: Event, idx: number): void {
    this.swap(e, idx, -1);
  }

  moveDown(e: Event, idx: number): void {
    this.swap(e, idx, 1);
  }

  toggleEditing() {
    this.editing = !this.editing;
  }

  toggleAddTrigger() {
    this.showAddTrigger = !this.showAddTrigger;
  }

  saveStep(step: Step) {
    return this.httpService.requestUpdateAdminQuestionnaireStep(step.id, step).subscribe(_ => {
      this.toggleEditing();
    });
  }

  deleteStep(step: Step) {
    this.openConfirmableModalDialog(step, "").subscribe();
  }

  openConfirmableModalDialog(arg: Step, scope: any): Observable<string> {
    scope = !scope ? this : scope;
    return new Observable((observer) => {
      const modalRef = this.modalService.open(DeleteConfirmationComponent, {backdrop: 'static', keyboard: false});
      modalRef.componentInstance.arg = arg;
      modalRef.componentInstance.scope = scope;

      modalRef.componentInstance.confirmFunction = () => {
        observer.complete()
        return this.httpService.requestDeleteAdminQuestionareStep(arg.id).subscribe(_ => {
          this.utilsService.deleteResource(this.steps, arg);
        });
      };
    });
  }

  addTrigger() {
    this.step.triggered_by_options.push(this.new_trigger);
    this.toggleAddTrigger();
    this.new_trigger = {"field": "", "option": "", "sufficient": true};
  }

  delTrigger(trigger: TriggeredByOption) {
    const index = this.step.triggered_by_options.indexOf(trigger);
    if (index !== -1) {
      this.step.triggered_by_options.splice(index, 1);
    }
  }
}