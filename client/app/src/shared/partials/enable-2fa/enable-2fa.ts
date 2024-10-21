import { Component, OnInit, inject } from "@angular/core";
import {UtilsService} from "@app/shared/services/utils.service";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import { FormBuilder, FormGroup, FormsModule, ReactiveFormsModule } from "@angular/forms";
import {TwoFactorAuthData} from "@app/services/helper/2fa.data.service";
import { QRCodeModule } from "angularx-qrcode";
import { NgClass } from "@angular/common";
import { TranslateModule } from "@ngx-translate/core";
import { TranslatorPipe } from "@app/shared/pipes/translate";

@Component({
    selector: "src-enable-2fa",
    templateUrl: "./enable-2fa.html",
    standalone: true,
    imports: [QRCodeModule, FormsModule, ReactiveFormsModule, NgClass, TranslateModule, TranslatorPipe]
})
export class Enable2fa implements OnInit{
  protected utils = inject(UtilsService);
  protected preferenceResolver = inject(PreferenceResolver);
  private builder = inject(FormBuilder);
  protected twoFactorAuthData = inject(TwoFactorAuthData);


  symbols = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  array = new Uint32Array(32);
  OTPSecretForm: FormGroup;

  constructor() {
    this.initialization();
  }

  ngOnInit() {
    this.OTPSecretForm = this.builder.group({});
  };

  initialization() {
    window.crypto.getRandomValues(this.array);

    for (let i = 0; i < this.array.length; i++) {
      this.twoFactorAuthData.totp.secret += this.symbols[this.array[i] % this.symbols.length];
    }

    this.onSecretKeyChanged();
  }

  onSecretKeyChanged() {
    this.twoFactorAuthData.totp.qrcode_string = "otpauth://totp/" + location.host + "%20%28" + this.preferenceResolver.dataModel.username + "%29?secret=" + this.twoFactorAuthData.totp.secret;
  }
}
