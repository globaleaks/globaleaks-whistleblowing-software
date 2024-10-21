import { Component, Input, inject } from "@angular/core";
import {AppDataService} from "@app/app-data.service";
import {HttpService} from "@app/shared/services/http.service";
import {NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {UtilsService} from "@app/shared/services/utils.service";
import {DeleteConfirmationComponent} from "@app/shared/modals/delete-confirmation/delete-confirmation.component";
import {Observable} from "rxjs";
import {Status} from "@app/models/app/public-model";
import { FormsModule } from "@angular/forms";

import { SubStatusComponent } from "../substatuses/sub-status.component";
import { TranslatorPipe } from "@app/shared/pipes/translate";

@Component({
    selector: "src-substatusmanager",
    templateUrl: "./sub-status-manager.component.html",
    standalone: true,
    imports: [FormsModule, SubStatusComponent, TranslatorPipe]
})
export class SubStatusManagerComponent {
  private appDataServices = inject(AppDataService);
  private httpService = inject(HttpService);
  private modalService = inject(NgbModal);
  private utilsService = inject(UtilsService);

  editing = false;
  @Input() submissionsStatus: Status;
  @Input() submissionStatuses: Status[];
  @Input() index: number;
  @Input() first: boolean;
  @Input() last: boolean;

  isSystemDefined(state: Status): boolean {
    return ["new", "opened", "closed"].indexOf(state.id) !== -1;
  }

  toggleEditing(submissionsStatus: Status): void {
    if (this.isEditable(submissionsStatus)) {
      this.editing = !this.editing;
    }
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
    this.httpService.requestUpdateStatus(url, submissionsStatus).subscribe(_ => {
    });
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
        return this.utilsService.deleteStatus(url).subscribe(_ => {
          this.utilsService.deleteResource(this.submissionStatuses, arg);
        });
      };
    });
  }
}
