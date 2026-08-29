import {Component, OnInit, computed, inject, signal} from "@angular/core";
import {ActivatedRoute} from "@angular/router";
import {TranslatePipe} from "@ngx-translate/core";
import {NewUser} from "@app/models/admin/new-user";
import {User, UserProfile} from "@app/models/resolvers/user-resolver-model";
import {Constants} from "@app/shared/constants/constants";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {TenantsResolver} from "@app/shared/resolvers/tenants.resolver";
import {UsersResolver} from "@app/shared/resolvers/users.resolver";
import {HttpService} from "@app/shared/services/http.service";
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
export class UsersTab1Component implements OnInit {
  protected nodeResolver = inject(NodeResolver);
  private usersResolver = inject(UsersResolver);
  private tenantsResolver = inject(TenantsResolver);
  private httpService = inject(HttpService);
  private utilsService = inject(UtilsService);
  private activatedRoute = inject(ActivatedRoute);

  showAddUser = false;

  // A link may point at one user: the list opens on the page holding it and
  // shows its card open, so that the user is read where it is configured
  focusUserId = "";

  readonly tenantData = computed(() => this.tenantsResolver.resource.value());

  // The profiles of the tenant, by id: an account either points at one of them
  // or carries its own personal profile
  private readonly profilesById = signal<Record<string, UserProfile>>({});

  // The same row however often the list is laid out: the profile label arrives after the accounts
  protected readonly byId = (user: User) => user.id;

  readonly usersData = computed<User[]>(() => {
    const profilesById = this.profilesById();

    return this.usersResolver.resource.value().map(user => ({
      ...user,
      profile: profilesById[user.profile_id] || user.profile
    }));
  });

  readonly profiles = computed<UserProfile[]>(() => {
    const shared = this.profilesById();
    const personal = this.usersResolver.resource.value()
      .filter(user => user.profile && !shared[user.profile.id])
      .map(user => user.profile);

    return [...Object.values(shared), ...personal];
  });

  // A personal profile is never offered to another account
  readonly selectable_profiles = computed<UserProfile[]>(() => this.profiles().filter(profile => !profile.custom));

  new_user: { username: string, role: string, name: string, email: string, profile_id: string, send_activation_link: boolean } = {
    username: "",
    role: "",
    name: "",
    email: "",
    profile_id: "none",
    send_activation_link: true
  };
  editing = false;
  protected readonly Constants = Constants;

  ngOnInit(): void {
    this.loadProfiles();

    this.activatedRoute.queryParams.subscribe(params => {
      this.focusUserId = params["id"] || "";
    });
  }

  addUser(): void {
    const user: NewUser = new NewUser();

    // The profile select carries 'none' as the sentinel of "no profile": only a
    // profile actually present in the list dictates the role of the new user
    const profile = this.profiles().find(entry => entry.id === this.new_user.profile_id);

    user.role = profile ? profile.role : this.new_user.role;
    user.profile_id = profile ? profile.id : "";
    user.username = typeof this.new_user.username !== "undefined" ? this.new_user.username : "";
    user.name = this.new_user.name;
    user.mail_address = this.new_user.email;
    user.language = this.nodeResolver.dataModel.default_language;
    user.send_activation_link = this.new_user.send_activation_link;
    this.utilsService.addAdminUser(user).subscribe(() => {
      this.getResolver();
      this.new_user = {username: "", role: "", name: "", email: "", profile_id: "none", send_activation_link: true};
    });
  }

  getResolver(): void {
    this.usersResolver.refresh();
    this.loadProfiles();
  }

  toggleAddUser(): void {
    this.showAddUser = !this.showAddUser;
  }

  onDelete(id: string) {
   this.usersResolver.resource.update(users => users.filter(user => user.id !== id));
  }

  private loadProfiles(): void {
    this.httpService.requestUserProfilesResource().subscribe((profiles: UserProfile[]) => {
      this.profilesById.set(Object.fromEntries(profiles.map(profile => [profile.id, profile])));
    });
  }
}
