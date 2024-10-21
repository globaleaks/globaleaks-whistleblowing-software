import { Component, Input, OnInit, inject } from "@angular/core";
import {UtilsService} from "@app/shared/services/utils.service";
import {HttpClient} from "@angular/common/http";
import {NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {HttpService} from "@app/shared/services/http.service";
import {DeleteConfirmationComponent} from "@app/shared/modals/delete-confirmation/delete-confirmation.component";
import {Observable} from "rxjs";
import {Status, Substatus} from "@app/models/app/public-model";

import { FormsModule } from "@angular/forms";
import { TranslatorPipe } from "@app/shared/pipes/translate";

@Component({
    selector: "src-substatuses",
    templateUrl: "./sub-status.component.html",
    standalone: true,
    imports: [FormsModule, TranslatorPipe]
})
export class SubStatusComponent implements OnInit {
  private httpService = inject(HttpService);
  protected modalService = inject(NgbModal);
  protected utilsService = inject(UtilsService);
  private http = inject(HttpClient);

  @Input() submissionsStatus: Status;
  subStatusEditing: boolean[] = [];
  newSubStatus: { label: string; } = {label: ""};
  showAddSubStatus: boolean = false;

  toggleAddSubStatus(): void {
    this.showAddSubStatus = !this.showAddSubStatus;
  }

  ngOnInit(): void {
    this.subStatusEditing = new Array(this.submissionsStatus.substatuses.length).fill(false);
  }

  addSubmissionSubStatus(): void {
    const order = this.utilsService.newItemOrder(this.submissionsStatus.substatuses, "order");
    const newSubmissionsSubStatus = {
      label: this.newSubStatus.label,
      order: order,
      tip_timetolive: -1
    };

    this.http.post<any>(
      `api/admin/statuses/${this.submissionsStatus.id}/substatuses`,
      newSubmissionsSubStatus
    ).subscribe(
      result => {
        this.submissionsStatus.substatuses.push(result);
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

    if (target < 0 || target >= this.submissionsStatus.substatuses.length) {
      return;
    }

    const temp = this.submissionsStatus.substatuses[index];
    this.submissionsStatus.substatuses[index] = this.submissionsStatus.substatuses[target];
    this.submissionsStatus.substatuses[target] = temp;

    const ids = this.submissionsStatus.substatuses.map((c: Substatus) => c.id);

    this.http.put<any>(
      `api/admin/statuses/${this.submissionsStatus.id}/substatuses`,
      {
        operation: "order_elements",
        args: {ids: ids}
      }
    ).subscribe();
  }

  saveSubmissionsSubStatus(subStatusParam: Substatus): void {
    if (subStatusParam.tip_timetolive_option <= -1) {
      subStatusParam.tip_timetolive = -1;
    } else if (subStatusParam.tip_timetolive_option === 0) {
      subStatusParam.tip_timetolive = 0;
    }
    const url = "api/admin/statuses/" + this.submissionsStatus.id + "/substatuses/" + subStatusParam.id;
    this.httpService.requestUpdateStatus(url, subStatusParam).subscribe(_ => {
    });
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

  toggleSubstatusEditing(index: number): void {
    this.subStatusEditing[index] = !this.subStatusEditing[index];
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
        return this.utilsService.deleteSubStatus(url).subscribe(_ => {
          this.utilsService.deleteResource(this.submissionsStatus.substatuses, arg);
        });
      };
    });
  }
}
