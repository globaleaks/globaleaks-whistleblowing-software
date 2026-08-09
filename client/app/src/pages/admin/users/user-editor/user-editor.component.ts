import {Component, ElementRef, OnInit, inject, input, viewChild, output} from "@angular/core";
import {TranslatePipe} from "@ngx-translate/core";
import {NgForm, FormsModule} from "@angular/forms";
import {NgbModal, NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {AppDataService} from "@app/app-data.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {Constants} from "@app/shared/constants/constants";
import {DeleteConfirmationComponent} from "@app/shared/modals/delete-confirmation/delete-confirmation.component";
import {PasswordSetComponent} from "@app/shared/modals/password-set/password-set.component";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import {Observable} from "rxjs";
import {User, UserProfile} from "@app/models/resolvers/user-resolver-model";
import {nodeResolverModel} from "@app/models/resolvers/node-resolver-model";
import {preferenceResolverModel} from "@app/models/resolvers/preference-resolver-model";
import {DatePipe} from "@angular/common";
import {ImageUploadDirective} from "@app/shared/directive/image-upload.directive";
import {CryptoService} from "@app/shared/services/crypto.service";
import {ListItemComponent} from "@app/shared/components/list-item/list-item.component";

@Component({
    selector: "src-user-editor",
    templateUrl: "./user-editor.component.html",
    standalone: true,
    imports: [TranslatePipe, ImageUploadDirective, FormsModule, NgbTooltipModule, DatePipe, ListItemComponent]
})
export class UserEditorComponent implements OnInit {
  private modalService = inject(NgbModal);
  private appDataService = inject(AppDataService);
  private preference = inject(PreferenceResolver);
  private authenticationService = inject(AuthenticationService);
  private nodeResolver = inject(NodeResolver);
  protected utilsService = inject(UtilsService);
  private cryptoService = inject(CryptoService);
  protected preferenceResolver = inject(PreferenceResolver);
  private elementRef = inject(ElementRef);

  readonly user = input.required<User>();
  readonly users = input<User[]>();
  readonly index = input<number>();
  readonly editUser = input.required<NgForm>();
  readonly profiles = input<UserProfile[]>([]);
  // A link pointing at this user opens its card and brings it into view
  readonly expanded = input(false);
  readonly deleted = output<string>();
  readonly uploaderInput = viewChild<ElementRef>("uploader");
  editing = false;
  filteredProfiles: UserProfile[];
  changePasswordArgs: { password_change_needed: string };
  nodeData: nodeResolverModel;
  preferenceData: preferenceResolverModel;
  authenticationData: AuthenticationService;
  appServiceData: AppDataService;
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
    this.changePasswordArgs = {
      password_change_needed: ""
    };

    this.user().profile = this.profiles().filter(profile => profile.id === this.user().profile_id)[0];
    this.normalizeForwardingProfilePermissions(this.user().profile);
    this.filteredProfiles = this.profiles().filter(profile => !profile.custom);

    if (this.expanded()) {
      this.editing = true;
      // The card is reached from elsewhere: it is brought into view once the
      // list holding it has been laid out
      setTimeout(() => this.elementRef.nativeElement.scrollIntoView({behavior: "smooth", block: "start"}));
    }
  }

  disable2FA(user: User) {
    this.utilsService.runAdminOperation("disable_2fa", {"value": user.id}, false).subscribe(() => {
      user.two_factor = false;
    });
  }

  resetIdpBinding(user: User) {
    this.utilsService.runAdminOperation("reset_idp_binding", {"value": user.id}, true).subscribe();
  }

  async setPassword(user: User) {
    // Generate a random password on the client. The plaintext is shown to the
    // administrator only after the change has been confirmed and applied so
    // that it can be communicated to the user; only the derived hash is sent.
    const password = this.cryptoService.generatePassword();

    let hash: string;
    this.appDataService.updateShowLoadingPanel(true);
    try {
      hash = await this.cryptoService.hashArgon2(password, user.salt);
    } finally {
      this.appDataService.updateShowLoadingPanel(false);
    }

    this.utilsService.runAdminOperation("set_user_password", {user_id: user.id, password: hash}, false).subscribe(() => {
      const modalRef = this.modalService.open(PasswordSetComponent, {backdrop: "static", keyboard: false, ariaLabelledBy: "modal-title"});
      modalRef.componentInstance.password = password;
    });
  }

  saveUser(userData: User) {
    this.normalizeForwardingProfilePermissions(userData.profile);
    const user = userData;
    if (user.pgp_key_remove) {
      user.pgp_key_public = "";
    }

    if (user.pgp_key_public !== "") {
      user.pgp_key_remove = false;
    }

    return this.utilsService.updateAdminUser(userData.id, userData).subscribe({
      error:()=>{
        const uploaderInput = this.uploaderInput();
        if (uploaderInput) {
          uploaderInput.nativeElement.value = "";
        }
      }
    });
  }

  deleteUser(user: User, statsChanged = false) {
    this.openConfirmableModalDialog(user, statsChanged).subscribe();
  }

  openConfirmableModalDialog(arg: User, statsChanged = false): Observable<string> {
    return new Observable((observer) => {
      const modalRef = this.modalService.open(DeleteConfirmationComponent, {backdrop: 'static', keyboard: false});
      modalRef.componentInstance.user = arg;
      modalRef.componentInstance.statsChanged = statsChanged;

      modalRef.componentInstance.confirmFunction = () => {
        const stats = modalRef.componentInstance.userStats;
        observer.complete();

        return this.utilsService.deleteAdminUser(arg.id, stats).subscribe({
          next: () => {
            this.deleted.emit(this.user().id);
          },
          error: (err) => {
            if (err.status === 409) {
              this.deleteUser(arg, true);
            }
          }
        });
      };
    });
  }

  resetUserPassword(user: User) {
    this.utilsService.runAdminOperation("send_password_reset_email", {"value": user.id}, true).subscribe();
  }

  loadPublicKeyFile(files: FileList | null, user:User) {
    if (files && files.length > 0) {
      this.utilsService.readFileAsText(files[0])
        .subscribe((txt: string) => {
          this.user().pgp_key_public = txt;
          return this.saveUser(user);
        });
    }
  };

  getUserID() {
    return this.authenticationData.session?.user_id;
  }

  getUserProfile(profileId: string): UserProfile | undefined {
    return this.profiles().find((profile) => profile.id === profileId);
  }

  getUserRoleOrProfileLabel(user: any): string {
    const roleMap: { [key: string]: string } = {
      'admin': 'Admin',
      'analyst': 'Analyst',
      'custodian': 'Custodian',
      'receiver': 'Recipient'
    };

    if (user.id == user.profile_id) {
      return roleMap[user.role];
    } else {
      return this.getUserProfile(user.profile_id)!.name;
    }
  }

  getUserDisplayName(user:any) {
    const profileName = this.getUserProfile(user.profile_id)!.name;

    let roleDisplay = '';
    switch (user.role) {
      case 'admin':
        roleDisplay = 'Admin';
        break;
      case 'receiver':
        roleDisplay = 'Recipient';
        break;
      case 'custodian':
        roleDisplay = 'Custodian';
        break;
      case 'analyst':
        roleDisplay = 'Analyst';
        break;
      default:
        roleDisplay = '';
    }

    return user.id !== user.profile_id ? `${profileName} (${roleDisplay})` : roleDisplay;
  }

  onUserProfileChange() {
    const profile = this.getUserProfile(this.user().profile_id);

    if (profile) {
        this.user().profile = profile;
        this.user().role = profile.role;
    }
  }

  toggleUserEscrow(user: User) {
    this.utilsService.runAdminOperation("toggle_user_escrow", {"value": user.id}, true).subscribe({
      error:()=>{
        user.escrow = !user.escrow;
      }
    });
  }

  normalizeForwardingProfilePermissions(profile: UserProfile) {
    if (profile.tid === 1 || !profile?.permissions?.can_forward_reports) {
      return;
    }

    profile.permissions.can_mask_information = false;
    profile.permissions.can_redact_information = false;
    profile.permissions.can_delete_submission = false;
  }
}
