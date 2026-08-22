import {Component} from "@angular/core";
import {TabsComponent} from "@app/shared/components/tabs/tabs.component";
import {TabDirective} from "@app/shared/components/tabs/tab.directive";
import {FormsModule} from "@angular/forms";
import {CaseManagementTab1Component} from "@app/pages/admin/casemanagement/casemanagement-tab1/case-management-tab1.component";

@Component({
    selector: "src-casemanagement",
    templateUrl: "./case-management.component.html",
    standalone: true,
    imports: [TabsComponent, TabDirective, FormsModule, CaseManagementTab1Component]
})
export class CaseManagementComponent {}
