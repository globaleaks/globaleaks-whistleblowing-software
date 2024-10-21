import {Component, inject} from "@angular/core";
import {AppDataService} from "@app/app-data.service";
import {HttpService} from "@app/shared/services/http.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {NgClass} from "@angular/common";
import {FormsModule} from "@angular/forms";
import {SubStatusManagerComponent} from "../substatusmanager/sub-status-manager.component";
import {TranslatorPipe} from "@app/shared/pipes/translate";

@Component({
    selector: "src-casemanagement-tab1",
    templateUrl: "./case-management-tab1.component.html",
    standalone: true,
    imports: [FormsModule, NgbTooltipModule, NgClass, SubStatusManagerComponent, TranslatorPipe]
})
export class CaseManagementTab1Component {
  private utilsService = inject(UtilsService);
  protected appDataServices = inject(AppDataService);
  private appDataService = inject(AppDataService);
  private httpService = inject(HttpService);

  showAddStatus = false;
  newSubmissionsStatus: { label: string; } = {label: ""};

  toggleAddStatus() {
    this.showAddStatus = !this.showAddStatus;
  };

  addSubmissionStatus() {
    const order = this.utilsService.newItemOrder(this.appDataServices.submissionStatuses, "order");
    const newSubmissionsStatus = {
      label: this.newSubmissionsStatus.label,
      order: order
    };

    this.httpService.addSubmissionStatus(newSubmissionsStatus).subscribe(
      result => {
        this.appDataService.submissionStatuses.push(result);
        this.newSubmissionsStatus.label = "";
      }
    );
  };
}
