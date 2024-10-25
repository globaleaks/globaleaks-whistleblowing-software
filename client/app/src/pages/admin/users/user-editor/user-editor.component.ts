import {Component, ElementRef, EventEmitter, Input, OnInit, Output, ViewChild} from "@angular/core";
import {NgForm} from "@angular/forms";
import {NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {AppDataService} from "@app/app-data.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {Constants} from "@app/shared/constants/constants";
import {DeleteConfirmationComponent} from "@app/shared/modals/delete-confirmation/delete-confirmation.component";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import {Observable} from "rxjs";
import {userResolverModel} from "@app/models/resolvers/user-resolver-model";
import {nodeResolverModel} from "@app/models/resolvers/node-resolver-model";
import {preferenceResolverModel} from "@app/models/resolvers/preference-resolver-model";

@Component({
  selector: "src-user-editor",
  templateUrl: "./user-editor.component.html"
})
export class UserEditorComponent implements OnInit {
  @Input() user: userResolverModel;
  @Input() users: userResolverModel[];
  @Input() index: number;
  @Input() editUser: NgForm;
  @Input() preferenceData: preferenceResolverModel;

  @Output() dataToParent = new EventEmitter<string>();
  @ViewChild("uploader") uploaderInput: ElementRef;
  editing = false;
  setPasswordArgs: { user_id: string, password: string };
  changePasswordArgs: { password_change_needed: string };
  passwordStrengthScore: number = 0;
  nodeData: nodeResolverModel;
  
  authenticationData: AuthenticationService;
  appServiceData: AppDataService;
  protected readonly Constants = Constants;

  constructor(private modalService: NgbModal, private appDataService: AppDataService,  protected authenticationService: AuthenticationService, private nodeResolver: NodeResolver, private utilsService: UtilsService) {
  }

  ngOnInit(): void {
    if (this.nodeResolver.dataModel) {
      this.nodeData = this.nodeResolver.dataModel;
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
  }

  toggleEditing() {
    this.editing = !this.editing;
  }

  onPasswordStrengthChange(score: number) {
    this.passwordStrengthScore = score;
  }

  disable2FA(user: userResolverModel) {
    this.utilsService.runAdminOperation("disable_2fa", {"value": user.id}, true).subscribe();
  }

  setPassword(setPasswordArgs: { user_id: string, password: string }) {
    this.utilsService.runAdminOperation("set_user_password", setPasswordArgs, false).subscribe();
    this.user.newpassword = false;
    this.setPasswordArgs.password = "";
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

  deleteUser(user: userResolverModel) {
    this.openConfirmableModalDialog(user, "").subscribe();
  }

  openConfirmableModalDialog(arg: userResolverModel, scope: any): Observable<string> {
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

  resetUserPassword(user: userResolverModel) {
    this.utilsService.runAdminOperation("send_password_reset_email", {"value": user.id}, true).subscribe();
  }

  loadPublicKeyFile(files: FileList | null,user:userResolverModel) {
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

  toggleUserEscrow(user: userResolverModel) {
    this.user.escrow = !this.user.escrow;
    this.utilsService.runAdminOperation("toggle_user_escrow", {"value": user.id}, true).subscribe();
  }
}