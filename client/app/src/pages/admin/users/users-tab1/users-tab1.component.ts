import {Component, OnInit} from "@angular/core";
import { AppDataService } from "@app/app-data.service";
import {NewUser} from "@app/models/admin/new-user";
import { preferenceResolverModel } from "@app/models/resolvers/preference-resolver-model";
import {tenantResolverModel} from "@app/models/resolvers/tenant-resolver-model";
import {userResolverModel} from "@app/models/resolvers/user-resolver-model";
import { AuthenticationService } from "@app/services/helper/authentication.service";
import {Constants} from "@app/shared/constants/constants";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import { PreferenceResolver } from "@app/shared/resolvers/preference.resolver";
import {TenantsResolver} from "@app/shared/resolvers/tenants.resolver";
import {UsersResolver} from "@app/shared/resolvers/users.resolver";
import {HttpService} from "@app/shared/services/http.service";
import {UtilsService} from "@app/shared/services/utils.service";

@Component({
  selector: "src-users-tab1",
  templateUrl: "./users-tab1.component.html"
})
export class UsersTab1Component implements OnInit {
  showAddUser = false;
  tenantData: tenantResolverModel;
  preferenceData: preferenceResolverModel;
  usersData: userResolverModel[];
  new_user: { username: string, role: string, idp_id: string, name: string, email: string } = {
    username: "",
    role: "",
    idp_id: "",
    name: "",
    email: ""
  };
  editing = false;
  protected readonly Constants = Constants;

  constructor(private httpService: HttpService, protected nodeResolver: NodeResolver, private usersResolver: UsersResolver, private tenantsResolver: TenantsResolver, private utilsService: UtilsService, protected authenticationService: AuthenticationService, private preference: PreferenceResolver, protected appDataService: AppDataService) {
  }

  ngOnInit(): void {
    if (this.usersResolver.dataModel) {
      this.usersData = this.usersResolver.dataModel;
    }
    if (this.nodeResolver.dataModel.root_tenant) {
      this.tenantData = this.tenantsResolver.dataModel;
    }
    if(this.preference.dataModel){
      this.preferenceData = this.preference.dataModel
    }
  }

  addUser(): void {
    const user: NewUser = new NewUser();

    user.username = typeof this.new_user.username !== "undefined" ? this.new_user.username : "";
    user.role = this.new_user.role;
    user.idp_id = this.new_user.idp_id;
    user.name = this.new_user.name;
    user.mail_address = this.new_user.email;
    user.language = this.nodeResolver.dataModel.default_language;
    this.utilsService.addAdminUser(user).subscribe(_ => {
      this.getResolver();
      this.new_user = {username: "", role: "", idp_id: "", name: "", email: ""};
    });
  }

  getResolver() {
    return this.httpService.requestUsersResource().subscribe(response => {
      this.usersResolver.dataModel = response;
      this.usersData = response;
    });
  }

  toggleAddUser(): void {
    this.showAddUser = !this.showAddUser;
  }
}