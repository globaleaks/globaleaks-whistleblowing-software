import {Component, OnInit, inject, input, output} from "@angular/core";
import {TranslatePipe} from "@ngx-translate/core";
import {UtilsService} from "@app/shared/services/utils.service";
import {NgbModal, NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {HttpService} from "@app/shared/services/http.service";
import {DeleteConfirmationComponent} from "@app/shared/modals/delete-confirmation/delete-confirmation.component";
import {Observable} from "rxjs";
import {Status, Substatus} from "@app/models/app/public-model";

import {FormsModule} from "@angular/forms";
import {ListItemComponent} from "@app/shared/components/list-item/list-item.component";

@Component({
    selector: "src-substatuses",
    templateUrl: "./sub-status.component.html",
    standalone: true,
    imports: [TranslatePipe, FormsModule, NgbTooltipModule, ListItemComponent]
})
export class SubStatusComponent implements OnInit {
  private httpService = inject(HttpService);
  protected modalService = inject(NgbModal);
  protected utilsService = inject(UtilsService);

  readonly submissionsStatus = input.required<Status>();
  readonly deleted = output<string>();
  subStatusEditing: boolean[] = [];
  newSubStatus: { label: string; } = {label: ""};
  showAddSubStatus = false;

  toggleAddSubStatus(): void {
    this.showAddSubStatus = !this.showAddSubStatus;
  }

  ngOnInit(): void {
    this.subStatusEditing = new Array(this.submissionsStatus().substatuses.length).fill(false);
  }

  addSubmissionSubStatus(): void {
    const order = this.utilsService.newItemOrder(this.submissionsStatus().substatuses, "order");
    const newSubmissionsSubStatus = {
      label: this.newSubStatus.label,
      order: order,
      tip_timetolive: -1
    };

    this.httpService.requestAddAdminSubstatus(
      this.submissionsStatus().id,
      newSubmissionsSubStatus
    ).subscribe(
      result => {
        this.submissionsStatus().substatuses.push(result);
        this.newSubStatus.label = "";
      }
    );
  }

  isCustomOptionSelected(tip_timetolive_option:string|number): boolean {
    return Number(tip_timetolive_option) === 0;
  }

  swapSs($event: Event, index: number, n: number): void {
    $event.stopPropagation();

    const target = index + n;

    if (target < 0 || target >= this.submissionsStatus().substatuses.length) {
      return;
    }

    const temp = this.submissionsStatus().substatuses[index];
    this.submissionsStatus().substatuses[index] = this.submissionsStatus().substatuses[target];
    this.submissionsStatus().substatuses[target] = temp;

    const ids = this.submissionsStatus().substatuses.map((c: Substatus) => c.id);

    this.httpService.requestReorderAdminSubstatuses(
      this.submissionsStatus().id,
      {
        operation: "order_elements",
        args: {ids: ids}
      }
    ).subscribe();
  }

  saveSubmissionsSubStatus(subStatusParam: Substatus): void {
    if (subStatusParam.tip_timetolive_option <= -1 || subStatusParam.tip_timetolive <= 0) {
      subStatusParam.tip_timetolive_option = subStatusParam.tip_timetolive = -1;
    }
    const url = "api/admin/statuses/" + this.submissionsStatus().id + "/substatuses/" + subStatusParam.id;
    this.httpService.requestUpdateStatus(url, subStatusParam).subscribe();
  }

  deleteSubSubmissionStatus(subStatusParam: Substatus): void {
    this.openConfirmableModalDialog(subStatusParam, "").subscribe();
  }

  moveSsUp(e: Event, idx: number): void {
    this.swapSs(e, idx, -1);
  }

  moveSsDown(e: Event, idx: number): void {
    this.swapSs(e, idx, 1);
  }

  openConfirmableModalDialog(arg: Substatus, scope: any): Observable<string> {
    scope = !scope ? this : scope;
    return new Observable((observer) => {
      const modalRef = this.modalService.open(DeleteConfirmationComponent, {backdrop: 'static', keyboard: false});
      modalRef.componentInstance.arg = arg;
      modalRef.componentInstance.scope = scope;
      modalRef.componentInstance.confirmFunction = () => {
        observer.complete()
        const url = "api/admin/statuses/" + arg.submissionstatus_id + "/substatuses/" + arg.id;
        return this.utilsService.deleteSubStatus(url).subscribe(() => {
          this.deleted.emit(arg.id);
        });
      };
    });
  }
}
