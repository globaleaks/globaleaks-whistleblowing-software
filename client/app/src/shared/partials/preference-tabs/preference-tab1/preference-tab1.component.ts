import { ChangeDetectorRef, Component, ElementRef, OnInit, ViewChild, inject } from "@angular/core";
import {AppConfigService} from "@app/services/root/app-config.service";
import {Constants} from "@app/shared/constants/constants";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {AppDataService} from "@app/app-data.service";
import {NgbModal, NgbModalRef} from "@ng-bootstrap/ng-bootstrap";
import {Enable2faComponent} from "@app/shared/modals/enable2fa/enable2fa.component";
import {TwoFactorAuthData} from "@app/services/helper/2fa.data.service";
import {HttpService} from "@app/shared/services/http.service";
import {
  EncryptionRecoveryKeyComponent
} from "@app/shared/modals/encryption-recovery-key/encryption-recovery-key.component";
import {TranslationService} from "@app/services/helper/translation.service";
import { TranslateService, TranslateModule } from "@ngx-translate/core";
import {ConfirmationWith2faComponent} from "@app/shared/modals/confirmation-with2fa/confirmation-with2fa.component";
import {
  ConfirmationWithPasswordComponent
} from "@app/shared/modals/confirmation-with-password/confirmation-with-password.component";
import { NgClass, DatePipe } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { TranslatorPipe } from "@app/shared/pipes/translate";

@Component({
    selector: "src-preference-tab1",
    templateUrl: "./preference-tab1.component.html",
    standalone: true,
    imports: [FormsModule, NgClass, DatePipe, TranslateModule, TranslatorPipe]
})
export class PreferenceTab1Component implements OnInit {
  private translationService = inject(TranslationService);
  protected appConfigService = inject(AppConfigService);
  private cdr = inject(ChangeDetectorRef);
  private translateService = inject(TranslateService);
  private httpService = inject(HttpService);
  private twoFactorAuthData = inject(TwoFactorAuthData);
  private modalService = inject(NgbModal);
  appDataService = inject(AppDataService);
  protected preferenceResolver = inject(PreferenceResolver);
  private utilsService = inject(UtilsService);
  protected authenticationService = inject(AuthenticationService);


  protected readonly Constants = Constants;

  editingName: boolean;
  editingPublicName: boolean;
  editingEmailAddress: boolean;
  languageModel = "";
  role = "";
  @ViewChild('uploader') uploaderInput: ElementRef<HTMLInputElement>;

  constructor() {
    this.languageModel = this.preferenceResolver.dataModel.language;
  }

  ngOnInit(): void {
    this.role = this.utilsService.rolel10n(this.authenticationService.session.role);
    this.role = this.translateService.instant(this.role);
    setTimeout(() => {
      this.languageModel = this.preferenceResolver.dataModel.language;
    }, 150);
  }

  toggleNameEditing() {
    this.editingName = !this.editingName;
  };

  togglePublicNameEditing() {
    this.editingPublicName = !this.editingPublicName;
  };

  toggleEmailAddressEditing() {
    this.editingEmailAddress = !this.editingEmailAddress;
  };

  toggle2FA(event: Event) {
    if (!this.preferenceResolver.dataModel.two_factor) {
      const array = new Uint32Array(32);

      window.crypto.getRandomValues(array);

      this.twoFactorAuthData.totp.secret = "";
      this.twoFactorAuthData.totp.qrcode_string = "";
      this.twoFactorAuthData.totp.edit = false;

      this.modalService.open(Enable2faComponent, {backdrop: 'static', keyboard: false});

    } else {
      const modalRef = this.modalService.open(ConfirmationWith2faComponent, {backdrop: 'static', keyboard: false});
      modalRef.result.then(
        (result) => {
          if (result) {
            const data = {
              "operation": "disable_2fa",
              "args": {
                "secret": result,
                "token": this.twoFactorAuthData.totp.token
              }
            };

            this.httpService.requestOperationsRecovery(data, this.utilsService.encodeString(result)).subscribe(
              {
                next: _ => {
                  this.preferenceResolver.dataModel.two_factor = !this.preferenceResolver.dataModel.two_factor;
                  this.utilsService.reloadCurrentRoute();
                },
                error: (_: any) => {
                 this.toggle2FA(event);
                }
              }
            );
          }
        },
        (_) => {
        }
      );
    }

    event.preventDefault();
    return false;
  }

  getEncryptionRecoveryKeyTrigger(result: any, event: Event) {
    const data = {
      "operation": "get_recovery_key",
      "args": {
        "secret": this.twoFactorAuthData.totp.secret,
        "token": this.twoFactorAuthData.totp.token
      }
    };

    this.httpService.requestOperationsRecovery(data, this.utilsService.encodeString(result)).subscribe(
      {
        next: response => {
          this.preferenceResolver.dataModel.clicked_recovery_key = true;
          const erk = response.data["text"].match(/.{1,4}/g).join("-");
          const modalRef = this.modalService.open(EncryptionRecoveryKeyComponent, {
            backdrop: 'static',
            keyboard: false
          });
          modalRef.componentInstance.erk = erk;
        },
        error: (error: any) => {
          if (error.error["error_message"] === "Authentication Failed" || error.error["error_message"] === "Two Factor authentication required") {
            this.getEncryptionRecoveryKey(event);
          } else {
            this.preferenceResolver.dataModel.clicked_recovery_key = true;
            const erk = error.error["text"].match(/.{1,4}/g).join("-");
            const modalRef = this.modalService.open(EncryptionRecoveryKeyComponent, {
              backdrop: 'static',
              keyboard: false
            });
            modalRef.componentInstance.erk = erk;
          }
        }
      }
    );
  }

  getEncryptionRecoveryKey(event: Event) {

    let modalRef: NgbModalRef;
    if (this.preferenceResolver.dataModel.two_factor) {
      modalRef = this.modalService.open(ConfirmationWith2faComponent, {backdrop: 'static', keyboard: false});
      modalRef.result.then(
        (result) => {
          this.getEncryptionRecoveryKeyTrigger(result, event);
        }
      );
    } else {
      let modalRef = this.modalService.open(ConfirmationWithPasswordComponent, {backdrop: 'static', keyboard: false});
      if (this.preferenceResolver.dataModel.two_factor) {
        modalRef = this.modalService.open(ConfirmationWith2faComponent, {backdrop: 'static', keyboard: false});
      }

      modalRef.componentInstance.confirmFunction = (secret: string) => {
        this.getEncryptionRecoveryKeyTrigger(secret, event);
      };
    }
  }

  save() {
    if (this.preferenceResolver.dataModel.pgp_key_remove) {
      this.preferenceResolver.dataModel.pgp_key_public = "";
    }
    const requestObservable = this.httpService.updatePreferenceResource(JSON.stringify(this.preferenceResolver.dataModel));
    requestObservable.subscribe(
      {
        next: _ => {
          this.translationService.onChange(this.preferenceResolver.dataModel.language);
          this.cdr.detectChanges();
          sessionStorage.removeItem("default_language");
          this.translationService.onChange(this.languageModel);
          this.appConfigService.reinit(false);
          this.utilsService.reloadCurrentRouteFresh(true);
        },
        error: _ =>{
          if (this.uploaderInput) {
            this.uploaderInput.nativeElement.value = "";
          }
        }
      }
    );
  };

  loadPublicKeyFile(files: any) {
    if (files && files.length > 0) {
      this.utilsService.readFileAsText(files[0])
        .subscribe((txt: string) => {
          this.preferenceResolver.dataModel.pgp_key_public = txt;
          return this.save();
        });
    }
  };

  onlanguagechange() {
    this.preferenceResolver.dataModel.language = this.languageModel;
  }

}
