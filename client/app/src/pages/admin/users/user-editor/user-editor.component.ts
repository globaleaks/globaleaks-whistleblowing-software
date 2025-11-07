import {Component, ElementRef, EventEmitter, Input, OnInit, Output, ViewChild, inject} from "@angular/core";
import {NgForm, FormsModule} from "@angular/forms";
import {NgbModal, NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {AppDataService} from "@app/app-data.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {Constants} from "@app/shared/constants/constants";
import {DeleteConfirmationComponent} from "@app/shared/modals/delete-confirmation/delete-confirmation.component";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import {Observable} from "rxjs";
import {User, UserProfile} from "@app/models/resolvers/user-resolver-model";
import {nodeResolverModel} from "@app/models/resolvers/node-resolver-model";
import {preferenceResolverModel} from "@app/models/resolvers/preference-resolver-model";
import {NgClass, DatePipe, CommonModule} from "@angular/common";
import {ImageUploadDirective} from "@app/shared/directive/image-upload.directive";
import {PasswordStrengthValidatorDirective} from "@app/shared/directive/password-strength-validator.directive";
import {PasswordMeterComponent} from "@app/shared/components/password-meter/password-meter.component";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {CryptoService} from "@app/shared/services/crypto.service";

@Component({
    selector: "src-user-editor",
    templateUrl: "./user-editor.component.html",
    standalone: true,
    imports: [CommonModule, ImageUploadDirective, FormsModule, PasswordStrengthValidatorDirective, NgbTooltipModule, NgClass, PasswordMeterComponent, DatePipe, TranslatorPipe]
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

  @Input() user: User;
  @Input() users: User[];
  @Input() index: number;
  @Input() editUser: NgForm;
  @Input() profiles: UserProfile[];
  @Output() dataToParent = new EventEmitter<string>();
  @ViewChild("uploader") uploaderInput: ElementRef;
  editing = false;
  filteredProfiles: UserProfile[];
  setPasswordArgs: { user_id: string, password: string };
  changePasswordArgs: { password_change_needed: string };
  passwordStrengthScore = 0;
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
    this.setPasswordArgs = {
      user_id: this.user.id,
      password: ""
    };
    this.changePasswordArgs = {
      password_change_needed: ""
    };

    this.user.profile = this.profiles.filter(profile => profile.id == this.user.profile_id)[0];
    this.filteredProfiles = this.profiles.filter(p => p.custom === false);
  }

  toggleEditing() {
    this.editing = !this.editing;
  }

  onPasswordStrengthChange(score: number) {
    this.passwordStrengthScore = score;
  }

  disable2FA(user: User) {
    this.utilsService.runAdminOperation("disable_2fa", {"value": user.id}, true).subscribe();
  }

  async setPassword(setPasswordArgs: { user_id: string, password: string }) {
    this.appDataService.updateShowLoadingPanel(true);
    setPasswordArgs.password = await this.cryptoService.hashArgon2(setPasswordArgs.password, this.user.salt);
    this.appDataService.updateShowLoadingPanel(false);

    this.utilsService.runAdminOperation("set_user_password", setPasswordArgs, false).subscribe();
    this.user.newpassword = false;
    this.setPasswordArgs.password = "";
  }

  saveUser(userData: User) {
    const user = userData;
    if (user.pgp_key_remove) {
      user.pgp_key_public = "";
    }

    if (user.pgp_key_public !== "") {
      user.pgp_key_remove = false;
    }

    return this.utilsService.updateAdminUser(userData.id, userData).subscribe({
      next:()=>{
        this.sendDataToParent();
      },
      error:()=>{
        if (this.uploaderInput) {
          this.uploaderInput.nativeElement.value = "";
        }
      }
    });
  }

  sendDataToParent() {
    this.dataToParent.emit();
  }

  deleteUser(user: User) {
    this.openConfirmableModalDialog(user, "").subscribe();
  }

  openConfirmableModalDialog(arg: User, scope: any): Observable<string> {
    scope = !scope ? this : scope;
    return new Observable((observer) => {
      const modalRef = this.modalService.open(DeleteConfirmationComponent, {backdrop: 'static', keyboard: false});
      modalRef.componentInstance.arg = arg;
      modalRef.componentInstance.scope = scope;

      modalRef.componentInstance.confirmFunction = () => {
        observer.complete()
        return this.utilsService.deleteAdminUser(arg.id).subscribe(_ => {
          this.utilsService.deleteResource(this.users, arg);
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
          this.user.pgp_key_public = txt;
          return this.saveUser(user);
        });
    }
  };

  getUserID() {
    return this.authenticationData.session?.user_id;
  }

  getUserProfile(profileId: string): UserProfile | undefined {
    return this.profiles.find((p) => p.id === profileId);
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
    const profile = this.getUserProfile(this.user.profile_id);

    if (profile) {
        this.user.profile = profile;
        this.user.role = profile.role;
    }
  }

  toggleUserEscrow(user: User) {
    this.utilsService.runAdminOperation("toggle_user_escrow", {"value": user.id}, true).subscribe({
      next:()=>{},
      error:()=>{
        user.escrow = !user.escrow;
      }
    });
  }
}
