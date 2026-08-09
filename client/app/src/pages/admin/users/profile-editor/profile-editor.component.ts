import {CollapsibleCardComponent} from "@app/shared/components/collapsible-card/collapsible-card.component";
import {Component, EventEmitter, Input, OnInit, Output, inject} from "@angular/core";
import {NgForm, FormsModule} from "@angular/forms";
import {NgbModal, NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {AppDataService} from "@app/app-data.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {Constants} from "@app/shared/constants/constants";
import {DeleteConfirmationComponent} from "@app/shared/modals/delete-confirmation/delete-confirmation.component";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {SelectablesResolver} from "@app/shared/resolvers/selectables.resolver";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import {Observable} from "rxjs";
import {UserProfile} from "@app/models/resolvers/user-resolver-model";
import {nodeResolverModel} from "@app/models/resolvers/node-resolver-model";
import {preferenceResolverModel} from "@app/models/resolvers/preference-resolver-model";
import {NgClass, CommonModule} from "@angular/common";
import {SelectionEditorComponent, SelectionEntry} from "@app/shared/components/selection-editor/selection-editor.component";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-profile-editor",
    templateUrl: "./profile-editor.component.html",
    standalone: true,
    imports: [CollapsibleCardComponent, CommonModule, SelectionEditorComponent, FormsModule, NgbTooltipModule, NgClass, TranslateModule]
})
export class ProfileEditorComponent implements OnInit {
  private modalService = inject(NgbModal);
  private appDataService = inject(AppDataService);
  private preference = inject(PreferenceResolver);
  private authenticationService = inject(AuthenticationService);
  private nodeResolver = inject(NodeResolver);
  private selectablesResolver = inject(SelectablesResolver);
  protected utilsService = inject(UtilsService);

  @Input() profile: UserProfile;
  @Input() profiles: UserProfile[];
  @Input() index: number;
  @Input() editProfile: NgForm;
  @Output() dataToParent = new EventEmitter<string>();
  @Output() deleted = new EventEmitter<string>();
  editing = false;
  nodeData: nodeResolverModel;
  preferenceData: preferenceResolverModel;
  authenticationData: AuthenticationService;
  appServiceData: AppDataService;
  roles = [
       { value: 'admin', role: 'Admin' },
       { value: 'analyst', role: 'Analyst' },
       { value: 'custodian', role: 'Custodian' },
       { value: 'receiver', role: 'Recipient' }
     ];

  protected readonly Constants = Constants;

  ngOnInit(): void {
    if (this.nodeResolver.dataModel) {
      this.nodeData = this.nodeResolver.dataModel;
    }
    if (this.preference.dataModel) {
      this.preferenceData = this.preference.dataModel;
    }
    if (this.authenticationService) {
      this.authenticationData = this.authenticationService;
    }
    if (this.appDataService) {
      this.appServiceData = this.appDataService;
    }

    this.profile.roles.sort();

    if (Array.isArray(this.profile.roles)) {
      this.roles = this.roles.filter(r => !this.profile.roles.includes(r.value));
    }

    this.normalizeForwardingProfilePermissions(this.profile);
  }

  toggleEditing() {
    this.editing = !this.editing;
  }

  saveProfile(userData: UserProfile ) {
    this.normalizeForwardingProfilePermissions(userData);
    const user = userData;
    return this.utilsService.updateAdminUserProfile(userData.id, userData).subscribe({
      next:()=>{
        this.sendDataToParent();
      },
      error:()=>{
      }
    });
  }

  sendDataToParent() {
    this.dataToParent.emit();
  }

  deleteProfile(profile: UserProfile) {
    this.openConfirmableModalDialog(profile, "").subscribe();
  }

  openConfirmableModalDialog(arg: UserProfile, scope: any): Observable<string> {
    scope = !scope ? this : scope;
    return new Observable((observer) => {
      const modalRef = this.modalService.open(DeleteConfirmationComponent, {backdrop: 'static', keyboard: false});
      modalRef.componentInstance.arg = arg;
      modalRef.componentInstance.scope = scope;

      modalRef.componentInstance.confirmFunction = () => {
        observer.complete()
        return this.utilsService.deleteAdminUserProfile(arg.id).subscribe(_ => {
          this.deleted.emit(arg.id);
        });
      };
    });
  }

  getUserID() {
    return this.authenticationData.session?.user_id;
  }

  exportProfile(profile:UserProfile){
    this.utilsService.saveAs(this.authenticationService, profile.name + ".json", "api/admin/profiles/" + profile.id);
  }

  userIsNotAdmin(profile: any): boolean {
    return !profile.roles.includes('admin');
  }

  hasSpecificRole(profile: any): boolean {
    return profile.roles && profile.roles.some((role: string) => ['analyst', 'custodian', 'receiver'].includes(role));
  }

  get roleOptions(): SelectionEntry[] {
    return this.roles.map(r => ({id: r.value, label: r.role}));
  }

  get heldRoles(): SelectionEntry[] {
    return this.profile.roles.map(role => ({id: role, label: this.utilsService.getRoleDisplayName(role)}));
  }

  assignRole(role: string) {
    if (role && !this.profile.roles.includes(role)) {
      this.profile.roles.push(role);
      this.profile.roles.sort();
      this.roles = this.roles.filter(r => r.value !== role);
      if (!this.profile.role) {
        this.profile.role = role;
      }
    }
  }

  removeRole(index: number, role: string) {
    this.profile.roles.splice(index, 1);
    if (!this.roles.some(r => r.value === role)) {
      const displayName = role === 'receiver' ? 'Recipient' : role.charAt(0).toUpperCase() + role.slice(1);
      this.roles = [...this.roles, { value: role, role: displayName }];
    }
    if (this.profile.role === role) {
      this.profile.role = this.profile.roles[0] || '';
    }
  }

  setDefaultRole(role: string) {
    this.profile.role = role;
  }

  normalizeForwardingProfilePermissions(profile: UserProfile) {
    if (profile.tid === 1 || !profile.permissions.can_forward_reports) {
      return;
    }

    profile.permissions.can_mask_information = false;
    profile.permissions.can_redact_information = false;
    profile.permissions.can_delete_submission = false;
  }

  // The channels associated to the profile: the users holding it are the
  // receivers of them, on this tenant and on every tenant inheriting it
  get channelOptions(): SelectionEntry[] {
    const held = this.profile.contexts || [];
    return (this.selectablesResolver.dataModel.contexts || [])
      .filter(context => held.indexOf(context.id) === -1)
      .map(context => ({id: context.id, label: context.name}));
  }

  get heldChannels(): SelectionEntry[] {
    const held = this.profile.contexts || [];
    return (this.selectablesResolver.dataModel.contexts || [])
      .filter(context => held.indexOf(context.id) !== -1)
      .map(context => ({id: context.id, label: context.name}));
  }

  assignChannel(contextId: string) {
    if (!this.profile.contexts) {
      this.profile.contexts = [];
    }
    if (this.profile.contexts.indexOf(contextId) === -1) {
      this.profile.contexts.push(contextId);
    }
  }

  removeChannel(contextId: string) {
    this.profile.contexts = (this.profile.contexts || []).filter(id => id !== contextId);
  }
}
