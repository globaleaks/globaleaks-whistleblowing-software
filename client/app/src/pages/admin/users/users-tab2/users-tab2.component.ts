import {Component, ElementRef, OnInit, ViewChild, inject} from "@angular/core";
import {NewUserProfile} from "@app/models/admin/new-user";
import {tenantResolverModel} from "@app/models/resolvers/tenant-resolver-model";
import {UserProfile} from "@app/models/resolvers/user-resolver-model";
import {Constants} from "@app/shared/constants/constants";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {TenantsResolver} from "@app/shared/resolvers/tenants.resolver";
import {HttpService} from "@app/shared/services/http.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {FormsModule} from "@angular/forms";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {OrderByPipe} from "@app/shared/pipes/order-by.pipe";
import {ProfileEditorComponent} from "../profile-editor/profile-editor.component";
import {HttpClient} from "@angular/common/http";
import {FilterPipe} from "@app/shared/pipes/filter.pipe";
import {NgSelectComponent, NgOptionTemplateDirective} from "@ng-select/ng-select";

@Component({
  selector: 'src-users-tab2',
  standalone: true,
  imports: [FormsModule, NgbTooltipModule, ProfileEditorComponent, TranslatorPipe, OrderByPipe],
  templateUrl: './users-tab2.component.html',
})
export class UsersTab2Component implements OnInit {
  private httpService = inject(HttpService);
  protected nodeResolver = inject(NodeResolver);
  private tenantsResolver = inject(TenantsResolver);
  protected utilsService = inject(UtilsService);
  private http = inject(HttpClient);
  @ViewChild('keyUploadInput') keyUploadInput: ElementRef<HTMLInputElement>;

  showAddProfile = false;
  tenantData: tenantResolverModel;
  profilesData: UserProfile[]=[];
  new_profile: { name: string, role: string, roles: string [], permissions: []} = { name: "", role: "", roles: [], permissions: []};
  editing = false;
  selected = {value: []};
  roles: {value: string, role: string}[] = [];
  protected readonly Constants = Constants;

  ngOnInit(): void {
    this.getResolver();
    if (this.nodeResolver.dataModel.root_tenant) {
      this.tenantData = this.tenantsResolver.dataModel;
    }
  }

  addProfile(): void {
    const profile: NewUserProfile = new NewUserProfile();
    profile.name = this.new_profile.name;
    profile.role = this.new_profile.role;
    profile.roles = [this.new_profile.role];
    this.utilsService.addAdminUserProfile(profile).subscribe(_ => {
      this.getResolver();
      this.new_profile = {name: "", role: "", roles: [], permissions: []};
    });
  }

  importProfile(files: FileList | null) {
    if (files && files.length > 0) {
      this.utilsService.readFileAsText(files[0]).subscribe((txt) => {
        return this.http.post("api/admin/users/profiles", txt).subscribe({
          next:()=>{
            this.getResolver();
          },
          error:()=>{
            if (this.keyUploadInput) {
                this.keyUploadInput.nativeElement.value = "";
            }
          }
        });
      });
    }
  }

  getResolver() {
    return this.httpService.requestUserProfilesResource().subscribe((response: UserProfile[]) => {
      this.profilesData = response;
       this.roles = [
        {value:'admin', role: 'Admin'},
        {value:'analyst', role: 'Analyst'},
        {value:'custodian', role: 'Custodian'},
        {value:'receiver', role: 'Recipient'},
      ]
    });
  }

  assignRole(role: {value: string, role: string}) {
    if (role && !this.new_profile.roles.includes(role.value)) {
      this.new_profile.roles.push(role.value)
      if (!this.new_profile.role) {
        this.new_profile.role = role.value;
      }
      this.roles = this.roles.filter(r => r.value !== role.value);
    }
    this.selected.value = [];
  }

  setDefaultRole(role: string) {
    this.new_profile.role = role;
  }

  removeRole(index: number, role: string) {
     this.new_profile.roles.splice(index, 1);
     const displayRole = role === 'receiver' ? 'Recipient' : role.charAt(0).toUpperCase() + role.slice(1);
     if (!this.roles.some(r => r.value === role)) {
       this.roles = [...this.roles, { value: role, role: displayRole }];
     }
     if (this.new_profile.role === role) {
       this.new_profile.role = "";
     }
  }

  getRoleDisplayName(role: any): any {
    if (!role) return [];
    if (role === 'receiver') return 'Recipient';
    return role.charAt(0).toUpperCase() + role.slice(1);
  }

  toggleAddProfile(): void {
    this.showAddProfile = !this.showAddProfile;
  }
}
