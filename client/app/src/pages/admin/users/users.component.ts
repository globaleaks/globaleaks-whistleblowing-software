import {Component} from "@angular/core";
import {TabsComponent} from "@app/shared/components/tabs/tabs.component";
import {TabDirective} from "@app/shared/components/tabs/tab.directive";
import {UsersTab1Component} from "@app/pages/admin/users/users-tab1/users-tab1.component";
import {UsersTab2Component} from "@app/pages/admin/users/users-tab2/users-tab2.component";

@Component({
    selector: "src-users",
    templateUrl: "./users.component.html",
    standalone: true,
    imports: [TabsComponent, TabDirective, UsersTab1Component, UsersTab2Component]
})
export class UsersComponent {}
