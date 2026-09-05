import {Component, OnInit, inject, input, output} from "@angular/core";
import {DeleteConfirmationComponent} from "@app/shared/modals/delete-confirmation/delete-confirmation.component";
import {UtilsService} from "@app/shared/services/utils.service";
import {NgbModal, NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {FieldUtilitiesService} from "@app/shared/services/field-utilities.service";
import {HttpService} from "@app/shared/services/http.service";
import {Observable} from "rxjs";
import {Step, questionnaireResolverModel} from "@app/models/resolvers/questionnaire-model";
import {ParsedFields} from "@app/models/component-model/parsedFields";
import {TriggeredByOption} from "@app/models/app/shared-public-model";

import {FormsModule} from "@angular/forms";
import {ListItemComponent} from "@app/shared/components/list-item/list-item.component";
import {StepComponent} from "../step/step.component";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-steps-list",
    templateUrl: "./steps-list.component.html",
    standalone: true,
    imports: [FormsModule, NgbTooltipModule, StepComponent, TranslateModule, ListItemComponent]
})
export class StepsListComponent implements OnInit {
  private readonly utilsService = inject(UtilsService);
  private readonly modalService = inject(NgbModal);
  private readonly fieldUtilities = inject(FieldUtilitiesService);
  protected nodeResolver = inject(NodeResolver);
  private readonly httpService = inject(HttpService);

  readonly step = input.required<Step>();
  readonly steps = input<Step[]>();
  readonly questionnaire = input.required<questionnaireResolverModel>();
  readonly index = input.required<number>();
  readonly deleted = output<string>();
  editing = false;
  showAddTrigger = false;
  parsedFields: ParsedFields;
  new_trigger: { field: string; option: string; sufficient: boolean } = {
    field: "",
    option: "",
    sufficient: true,
  };

  ngOnInit(): void {
    this.recompute();
  }

  recompute(): void {
    this.parsedFields = this.fieldUtilities.parseQuestionnaire(this.questionnaire(), {
      fields: [],
      fields_by_id: {},
      options_by_id: {}
    });
  }

  swap($event: Event, index: number, n: number): void {
    this.utilsService.swap($event, index, n, this.questionnaire())
  }

  moveUp(e: Event, idx: number): void {
    this.swap(e, idx, -1);
  }

  moveDown(e: Event, idx: number): void {
    this.swap(e, idx, 1);
  }

  toggleAddTrigger() {
    this.showAddTrigger = !this.showAddTrigger;
  }

  saveStep(step: Step) {
    return this.httpService.requestUpdateAdminQuestionnaireStep(step.id, step).subscribe();
  }

  deleteStep(step: Step) {
    this.openConfirmableModalDialog(step, "").subscribe();
  }

  openConfirmableModalDialog(arg: Step, scope: any): Observable<string> {
    scope = !scope ? this : scope;
    return new Observable(() => {
      const modalRef = this.modalService.open(DeleteConfirmationComponent, {backdrop: 'static', keyboard: false});
      modalRef.componentInstance.arg = arg;
      modalRef.componentInstance.scope = scope;

      modalRef.componentInstance.confirmFunction = () => {
        return this.httpService.requestDeleteAdminQuestionareStep(arg.id).subscribe(() => {
          this.deleted.emit(this.step().id);
        });
      };
    });
  }

  addTrigger() {
    this.step().triggered_by_options.push(this.new_trigger);
    this.toggleAddTrigger();
    this.new_trigger = {"field": "", "option": "", "sufficient": true};
  }

  delTrigger(trigger: TriggeredByOption) {
    const index = this.step().triggered_by_options.indexOf(trigger);
    if (index !== -1) {
      this.step().triggered_by_options.splice(index, 1);
    }
  }
}
