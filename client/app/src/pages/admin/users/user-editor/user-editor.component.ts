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
import {userResolverModel} from "@app/models/resolvers/user-resolver-model";
import {nodeResolverModel} from "@app/models/resolvers/node-resolver-model";
import {preferenceResolverModel} from "@app/models/resolvers/preference-resolver-model";
import {DatePipe} from "@angular/common";
import {ImageUploadDirective} from "@app/shared/directive/image-upload.directive";
import {CryptoService} from "@app/shared/services/crypto.service";

@Component({
    selector: "src-user-editor",
    templateUrl: "./user-editor.component.html",
    standalone: true,
    imports: [TranslatePipe, ImageUploadDirective, FormsModule, NgbTooltipModule, DatePipe]
})
export class UserEditorComponent implements OnInit {
  private modalService = inject(NgbModal);
  private appDataService = inject(AppDataService);
  private preference = inject(PreferenceResolver);
  private authenticationService = inject(AuthenticationService);
  private nodeResolver = inject(NodeResolver);
  private utilsService = inject(UtilsService);
  private cryptoService = inject(CryptoService);

  readonly user = input.required<userResolverModel>();
  readonly users = input<userResolverModel[]>();
  readonly index = input<number>();
  readonly editUser = input.required<NgForm>();
  readonly deleted = output<string>();
  readonly uploaderInput = viewChild<ElementRef>("uploader");
  editing = false;
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
  }

  toggleEditing() {
    this.editing = !this.editing;
  }

  disable2FA(user: userResolverModel) {
    this.utilsService.runAdminOperation("disable_2fa", {"value": user.id}, false).subscribe(() => {
      user.two_factor = false;
    });
  }

  async setPassword(user: userResolverModel) {
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

  saveUser(userData: userResolverModel) {
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

  deleteUser(user: userResolverModel) {
    this.openConfirmableModalDialog(user, "").subscribe();
  }

  openConfirmableModalDialog(arg: userResolverModel, scope: any): Observable<string> {
    scope = !scope ? this : scope;
    return new Observable(() => {
      const modalRef = this.modalService.open(DeleteConfirmationComponent, {backdrop: 'static', keyboard: false});
      modalRef.componentInstance.arg = arg;
      modalRef.componentInstance.scope = scope;

      modalRef.componentInstance.confirmFunction = () => {
        return this.utilsService.deleteAdminUser(arg.id).subscribe(() => {
          this.deleted.emit(this.user().id);
        });
      };
    });
  }

  resetUserPassword(user: userResolverModel) {
    this.utilsService.runAdminOperation("send_password_reset_email", {"value": user.id}, true).subscribe();
  }

  loadPublicKeyFile(files: FileList | null,user:userResolverModel) {
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

  toggleUserEscrow(user: userResolverModel) {
    this.utilsService.runAdminOperation("toggle_user_escrow", {"value": user.id}, true).subscribe({
      error:()=>{
        user.escrow = !user.escrow;
      }
    });
  }
}
