import {Component, computed, inject} from "@angular/core";
import {TranslatePipe} from "@ngx-translate/core";
import {NewUser} from "@app/models/admin/new-user";
import {Constants} from "@app/shared/constants/constants";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {TenantsResolver} from "@app/shared/resolvers/tenants.resolver";
import {UsersResolver} from "@app/shared/resolvers/users.resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {FormsModule} from "@angular/forms";
import {UserEditorComponent} from "../user-editor/user-editor.component";
import {PaginatedInterfaceComponent} from "@app/shared/components/paginated-interface/paginated-interface.component";


@Component({
    selector: "src-users-tab1",
    templateUrl: "./users-tab1.component.html",
    standalone: true,
    imports: [TranslatePipe, FormsModule, NgbTooltipModule, PaginatedInterfaceComponent, UserEditorComponent]
})
export class UsersTab1Component {
  protected nodeResolver = inject(NodeResolver);
  private usersResolver = inject(UsersResolver);
  private tenantsResolver = inject(TenantsResolver);
  private utilsService = inject(UtilsService);

  showAddUser = false;
  readonly tenantData = computed(() => this.tenantsResolver.resource.value());
  readonly usersData = computed(() => this.usersResolver.resource.value());
  new_user: { username: string, role: string, name: string, email: string, send_activation_link: boolean } = {
    username: "",
    role: "",
    name: "",
    email: "",
    send_activation_link: true
  };
  editing = false;
  protected readonly Constants = Constants;

  addUser(): void {
    const user: NewUser = new NewUser();

    user.username = typeof this.new_user.username !== "undefined" ? this.new_user.username : "";
    user.role = this.new_user.role;
    user.name = this.new_user.name;
    user.mail_address = this.new_user.email;
    user.language = this.nodeResolver.dataModel.default_language;
    user.send_activation_link = this.new_user.send_activation_link;
    this.utilsService.addAdminUser(user).subscribe(() => {
      this.getResolver();
      this.new_user = {username: "", role: "", name: "", email: "", send_activation_link: true};
    });
  }

  getResolver(): void {
    this.usersResolver.refresh();
  }

  toggleAddUser(): void {
    this.showAddUser = !this.showAddUser;
  }

  onDelete(id: string) {
   this.usersResolver.resource.update(users => users.filter(user => user.id !== id));
  }
}
