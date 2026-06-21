import {Injectable} from "@angular/core";

@Injectable({
  providedIn: "root"
})
export class TwoFactorAuthData {

  totp = {
    qrcode_string: "",
    secret: "",
    token: ""
  };
}
