import {Component, inject} from "@angular/core";
import {TranslatePipe} from "@ngx-translate/core";
import {AppDataService} from "@app/app-data.service";
import {HttpService} from "@app/shared/services/http.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {FormsModule} from "@angular/forms";
import {SubStatusManagerComponent} from "../substatusmanager/sub-status-manager.component";

@Component({
    selector: "src-casemanagement-tab1",
    templateUrl: "./case-management-tab1.component.html",
    standalone: true,
    imports: [TranslatePipe, FormsModule, NgbTooltipModule, SubStatusManagerComponent]
})
export class CaseManagementTab1Component {
  private readonly utilsService = inject(UtilsService);
  protected appDataServices = inject(AppDataService);
  private readonly appDataService = inject(AppDataService);
  private readonly httpService = inject(HttpService);

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

  onDelete(id: string) {
    this.appDataServices.submissionStatuses = [...this.appDataServices.submissionStatuses.filter(i => i.id !== id)];
  }
}
