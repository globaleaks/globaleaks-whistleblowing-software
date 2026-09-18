import {Component} from "@angular/core";
import {TabsComponent} from "@app/shared/components/tabs/tabs.component";
import {TabDirective} from "@app/shared/components/tabs/tab.directive";
import {FormsModule} from "@angular/forms";
import {Tab1Component} from "@app/pages/admin/settings/tab1/tab1.component";

@Component({
    selector: "src-custodian-settings",
    templateUrl: "./settings.component.html",
    standalone: true,
    imports: [TabsComponent, TabDirective, FormsModule, Tab1Component]
})
export class CustodianSettingsComponent {}
