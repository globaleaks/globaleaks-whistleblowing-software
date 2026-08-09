import {Component, inject} from "@angular/core";
import {TabsComponent} from "@app/shared/components/tabs/tabs.component";
import {TabDirective} from "@app/shared/components/tabs/tab.directive";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {UsersTab1Component} from "@app/pages/admin/users/users-tab1/users-tab1.component";
import {UsersTab2Component} from "@app/pages/admin/users/users-tab2/users-tab2.component";
import {UsersTab3Component} from "@app/pages/admin/users/users-tab3/users-tab3.component";

@Component({
    selector: "src-users",
    templateUrl: "./users.component.html",
    standalone: true,
    imports: [TabsComponent, TabDirective, UsersTab1Component, UsersTab2Component, UsersTab3Component]
})
export class UsersComponent {
  private node = inject(NodeResolver);

  // A profile holds no accounts of its own: on it the page offers the
  // profiles alone
  protected get isTenant(): boolean {
    return !this.node.dataModel.is_profile;
  }
}
