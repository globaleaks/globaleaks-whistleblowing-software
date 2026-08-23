import {Component, inject, input, output} from "@angular/core";
import {TranslatePipe} from "@ngx-translate/core";
import {AppDataService} from "@app/app-data.service";
import {HttpService} from "@app/shared/services/http.service";
import {NgbModal, NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {UtilsService} from "@app/shared/services/utils.service";
import {DeleteConfirmationComponent} from "@app/shared/modals/delete-confirmation/delete-confirmation.component";
import {Observable} from "rxjs";
import {Status} from "@app/models/app/public-model";
import {FormsModule} from "@angular/forms";

import {SubStatusComponent} from "../substatuses/sub-status.component";
import {ListItemComponent} from "@app/shared/components/list-item/list-item.component";

@Component({
    selector: "src-substatusmanager",
    templateUrl: "./sub-status-manager.component.html",
    standalone: true,
    imports: [TranslatePipe, FormsModule, NgbTooltipModule, SubStatusComponent, ListItemComponent]
})
export class SubStatusManagerComponent {
  private appDataServices = inject(AppDataService);
  private httpService = inject(HttpService);
  private modalService = inject(NgbModal);
  private utilsService = inject(UtilsService);

  editing = false;
  readonly submissionsStatus = input.required<Status>();
  readonly submissionStatuses = input<Status[]>();
  readonly index = input.required<number>();
  readonly first = input<boolean>();
  readonly last = input<boolean>();
  readonly deleted = output<string>();

  isSystemDefined(state: Status): boolean {
    return ["new", "opened", "closed"].indexOf(state.id) !== -1;
  }

  isEditable(submissionsStatus: Status): boolean {
    return ["new", "opened"].indexOf(submissionsStatus.id) === -1;
  }

  moveUp(e: Event, idx: number): void {
    this.swap(e, idx, -1);
  }

  moveDown(e: Event, idx: number): void {
    this.swap(e, idx, 1);
  }

  ssIdx(ssID: string): number | undefined {
    for (let i = 0; i < this.appDataServices.submissionStatuses.length; i++) {
      const status = this.appDataServices.submissionStatuses[i];
      if (status.id === ssID) {
        return i;
      }
    }
    return undefined;
  }

  swap($event: Event, index: number, n: number): void {
    $event.stopPropagation();

    const target = index + n;

    if (target < 0 || target >= this.appDataServices.submissionStatuses.length) {
      return;
    }

    const origIndex = this.ssIdx(this.appDataServices.submissionStatuses[index].id);
    const origTarget = this.ssIdx(this.appDataServices.submissionStatuses[target].id);

    if (origIndex !== undefined && origTarget !== undefined) {
      const movingStatus = this.appDataServices.submissionStatuses[origIndex];
      this.appDataServices.submissionStatuses[origIndex] = this.appDataServices.submissionStatuses[origTarget];
      this.appDataServices.submissionStatuses[origTarget] = movingStatus;

      const reorderedIds = {
        ids: this.appDataServices.submissionStatuses
          .map((c: Status) => c.id)
          .filter((c: number | string) => c)
      };
      this.httpService.runOperation("api/admin/statuses", "order_elements", reorderedIds, false).subscribe();
    }
  }

  deleteSubmissionStatus(submissionsStatus: Status): void {
    this.openConfirmableModalDialog(submissionsStatus, "").subscribe();
  }

  saveSubmissionsStatus(submissionsStatus: Status): void {
    const url = "api/admin/statuses/" + submissionsStatus.id;
    this.httpService.requestUpdateStatus(url, submissionsStatus).subscribe();
  }

  openConfirmableModalDialog(arg: Status, scope: any): Observable<string> {
    scope = !scope ? this : scope;
    return new Observable((observer) => {
      const modalRef = this.modalService.open(DeleteConfirmationComponent, {backdrop: 'static', keyboard: false});
      modalRef.componentInstance.arg = arg;
      modalRef.componentInstance.scope = scope;
      modalRef.componentInstance.confirmFunction = () => {
        observer.complete()
        const url = "api/admin/statuses/" + arg.id;
        return this.utilsService.deleteStatus(url).subscribe(() => {
          this.deleted.emit(arg.id);
        });
      };
    });
  }

  //onDelete(id: string) {
  //  this.appDataServices.submissionStatuses = [...this.appDataServices.submissionStatuses.filter(i => i.id !== id)];
  //}
  onDelete(id: string) {
    this.submissionsStatus().substatuses = [...this.submissionsStatus().substatuses.filter(i => i.id !== id)];
  }
}
