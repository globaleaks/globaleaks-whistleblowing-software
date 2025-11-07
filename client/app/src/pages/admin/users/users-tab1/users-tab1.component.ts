import {Component, OnInit, inject} from "@angular/core";
import {NewUser} from "@app/models/admin/new-user";
import {tenantResolverModel} from "@app/models/resolvers/tenant-resolver-model";
import {User, UserProfile} from "@app/models/resolvers/user-resolver-model";
import {Constants} from "@app/shared/constants/constants";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {TenantsResolver} from "@app/shared/resolvers/tenants.resolver";
import {UsersResolver} from "@app/shared/resolvers/users.resolver";
import {HttpService} from "@app/shared/services/http.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {NgClass} from "@angular/common";
import {FormsModule} from "@angular/forms";
import {UserEditorComponent} from "../user-editor/user-editor.component";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {OrderByPipe} from "@app/shared/pipes/order-by.pipe";
import {switchMap} from 'rxjs/operators';

@Component({
    selector: "src-users-tab1",
    templateUrl: "./users-tab1.component.html",
    standalone: true,
    imports: [FormsModule, NgbTooltipModule, NgClass, UserEditorComponent, TranslatorPipe, OrderByPipe]
})
export class UsersTab1Component implements OnInit {
  private httpService = inject(HttpService);
  protected nodeResolver = inject(NodeResolver);
  private usersResolver = inject(UsersResolver);
  private tenantsResolver = inject(TenantsResolver);
  private utilsService = inject(UtilsService);

  showAddUser = false;
  tenantData: tenantResolverModel;
  users: User[];
  profiles: UserProfile[]=[];
  custom_profiles: UserProfile[]=[];
  selectable_profiles: UserProfile[]=[];

  new_user: { username: string, role: string, name: string, email: string, profile_id: string, profile: {}, send_activation_link: boolean } = {
    username: "",
    role: "",
    name: "",
    email: "",
    profile_id: "",
    profile: {},
    send_activation_link: true
  };
  editing = false;
  protected readonly Constants = Constants;

  ngOnInit(): void {
    this.getResolver();
    if (this.nodeResolver.dataModel.root_tenant) {
      this.tenantData = this.tenantsResolver.dataModel;
    }
  }

  addUser(): void {
    const user: NewUser = new NewUser();
    if (this.new_user.profile_id){
      const profile_User = this.profiles.filter(user => user.id == this.new_user.profile_id);
      user.role = this.new_user.profile_id ? profile_User[0].role : this.new_user.role;
    }
    else {
      user.role = this.new_user.role;
    }
    user.username = typeof this.new_user.username !== "undefined" ? this.new_user.username : "";
    user.profile_id = this.new_user.profile_id;
    user.name = this.new_user.name;
    user.mail_address = this.new_user.email;
    user.language = this.nodeResolver.dataModel.default_language;
    user.send_activation_link = this.new_user.send_activation_link;
    this.utilsService.addAdminUser(user).subscribe(_ => {
      this.getResolver();
      this.new_user = {username: "", role: "", name: "", email: "", profile_id: "", profile: {}, send_activation_link: true};
    });
  }

  getResolver() {
    this.httpService.requestUserProfilesResource().pipe(
      switchMap((profilesResponse: UserProfile[]) => {
        this.profiles = profilesResponse;
        this.custom_profiles = profilesResponse.filter(profile => profile.custom === true);
        this.selectable_profiles = profilesResponse.filter(profile => profile.custom === false);

        return this.httpService.requestUsersResource();
      })
    ).subscribe(usersResponse => {
      this.users = usersResponse;

      // Attach profiles to each user
      this.users.forEach((user: User) => {
        user.profile = this.custom_profiles.find(profile => profile.id === user.profile_id)!;
      });
    });
  }

  receiveData() {
    this.getResolver();
  }

  toggleAddUser(): void {
    this.showAddUser = !this.showAddUser;
  }
}
