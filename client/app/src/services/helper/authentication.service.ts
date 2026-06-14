import {Injectable, inject, SecurityContext} from "@angular/core";
import {LoginDataRef} from "@app/pages/auth/login/model/login-model";
import {HttpService} from "@app/shared/services/http.service";
import {firstValueFrom, of, Observable} from "rxjs";
import {finalize} from 'rxjs/operators';
import {ActivatedRoute, Router} from "@angular/router";
import {AppDataService} from "@app/app-data.service";
import {ErrorCodes} from "@app/models/app/error-code";
import {Session} from "@app/models/authentication/session";
import {TitleService} from "@app/shared/services/title.service";
import {HttpClient, HttpErrorResponse, HttpHeaders} from "@angular/common/http";
import {NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {OtkcAccessComponent} from "@app/shared/modals/otkc-access/otkc-access.component";
import {DomSanitizer} from '@angular/platform-browser';
import {CryptoService} from "@app/shared/services/crypto.service";

@Injectable({
  providedIn: "root"
})
export class AuthenticationService {
  private http = inject(HttpClient);
  private modalService = inject(NgbModal);
  private titleService = inject(TitleService);
  private activatedRoute = inject(ActivatedRoute);
  private httpService = inject(HttpService);
  private appDataService = inject(AppDataService);
  private router = inject(Router);
  private sanitizer = inject(DomSanitizer);
  private cryptoService = inject(CryptoService);

  public session: any = undefined;
  permissions: { can_upload_files: boolean }
  loginInProgress = false;
  requireAuthCode = false;
  loginData: LoginDataRef = new LoginDataRef();

  public reset() {
    this.loginInProgress = false;
    this.requireAuthCode = false;
    this.loginData = new LoginDataRef();
  };

  deleteSession() {
    const role = this.session ? this.session.role : 'recipient';

    this.session = null;

    if (role === "whistleblower") {
      window.location.replace("about:blank");
    } else {
      window.location.hash = "/login";
      window.location.reload();
    }
  };

  setSession(response: Session) {
    this.session = response;
  }

  resetPassword(username: string) {
    const param = JSON.stringify({"username": username});
    this.httpService.requestResetLogin(param).subscribe(
      {
        next: () => {
          this.router.navigate(["/login/passwordreset/requested"]).then();
        }
      }
    );
  }

  async login(tid?: number, username?: string, password?: string | undefined, authcode?: string | undefined, authtoken?: string | null, callback?: () => void) {
    this.appDataService.updateShowLoadingPanel(true);

    try {
      if (authcode === undefined) {
        authcode = "";
      }

      let requestObservable: Observable<Session>;
      if (authtoken) {
        requestObservable = this.httpService.requestAuthTokenLogin(JSON.stringify({"authtoken": authtoken}));
      } else {
        const authHeader = this.getHeader();
        if (password) {
            if (username === "whistleblower") {
              password = password.replace(/\D/g, "");
            }

            const res = await firstValueFrom(this.httpService.requestAuthType(JSON.stringify({'username': username !== "whistleblower" ? username : ""})));
            if (res.type == 'key') {
              this.appDataService.updateShowLoadingPanel(true);
              password = await this.cryptoService.hashArgon2(password, res.salt);
              this.appDataService.updateShowLoadingPanel(false);
            }
        }

        if (username === "whistleblower") {
          requestObservable = this.httpService.requestWhistleBlowerLogin(JSON.stringify({"receipt": password}), authHeader);
        } else {
          requestObservable = this.httpService.requestGeneralLogin(JSON.stringify({
            "tid": tid,
            "username": username,
            "password": password,
            "authcode": authcode
          }), authHeader);
        }
      }

      requestObservable.pipe(finalize(() => this.appDataService.updateShowLoadingPanel(false))).subscribe({
          next: (response: Session) => {
            if (response.redirect) {
              response.redirect = this.sanitizer.sanitize(SecurityContext.URL, response.redirect) || '';
              if (response.redirect) {
                this.router.navigate([response.redirect]).then();
              }
            }

            if (response.role === "whistleblower") {
              response.homepage = "/";
            } else {
               const role = response.role === "receiver" ? "recipient" : response.role;
               response.homepage = "/" + role + "/home";
               response.preferencespage = "/" + role + "/preferences";
            }

            this.setSession(response);

            if (response && response.properties && response.properties.receipt_change_needed) {
              const receipt = this.cryptoService.generateReceipt();
              const formattedReceipt = this.formatReceipt(receipt);

              const modalRef = this.modalService.open(OtkcAccessComponent,{backdrop: 'static', keyboard: false});
              modalRef.componentInstance.arg = {
                receipt: receipt,
                formatted_receipt: formattedReceipt
              };
              modalRef.componentInstance.confirmFunction = async () => {
                const res = await firstValueFrom(this.httpService.requestAuthType(JSON.stringify({'username': ''})));
                let newReceipt: string;
                if (res.type === 'key') {
                  newReceipt = await this.cryptoService.hashArgon2(receipt, res.salt);
                } else {
                  newReceipt = receipt;
                }
                this.http.put('api/whistleblower/operations', {
                  operation: 'change_receipt',
                  args: {receipt: newReceipt}
                  }).subscribe(() => {
                  this.titleService.setPage('tippage');
                  modalRef.close();
                });
              };
              return;
            }

            if (this.session.role === "whistleblower") {
              if (password) {
                // A receipt was provided: a real tip exists, whether this is a
                // plain whistleblower or a recipient operating on its behalf.
                this.titleService.setPage("tippage");
                this.router.navigate(['/']);
              } else if (this.session.properties.operator_session) {
                // Operator switch without a receipt: no tip yet, stay off tippage.
                this.router.navigate(['/']);
              }
            } else {
              if (!callback) {
                this.reset();

                if (this.session.properties.password_change_needed) {
                  // A confined session must reach the forced page directly: the
                  // role landing route runs sibling resolvers that the backend
                  // now rejects, which would otherwise tear down the session.
                  this.router.navigate(['/action/forcedpasswordchange']).then();
                } else if (this.session.properties.require_two_factor) {
                  this.router.navigate(['/action/forcedtwofactor']).then();
                } else {
                let redirect = this.activatedRoute.snapshot.queryParams['redirect'] || undefined;
                redirect = this.activatedRoute.snapshot.queryParams['redirect'] || '/';
                redirect = decodeURIComponent(redirect);

	        if (redirect !== "/") {
                  redirect = this.sanitizer.sanitize(SecurityContext.URL, redirect) || '';

                  // Honor only local redirects
                  if (redirect.startsWith("/")) {
                    this.router.navigate([redirect]);
                  }
                } else {
                this.router.navigate([this.session.homepage], {
                    queryParams: this.activatedRoute.snapshot.queryParams,
                    queryParamsHandling: "merge"
                  }).then();
                }
                }
              }
            }

            if (callback) {
              callback();
            }
          },
          error: (error: HttpErrorResponse) => {
            this.loginInProgress = false;
            if (error.error && error.error["error_code"]) {
              if (error.error["error_code"] === 4) {
                this.requireAuthCode = true;
              } else if (error.error["error_code"] !== 13) {
                this.reset();
              }
            }

            this.appDataService.errorCodes = new ErrorCodes(error.error["error_message"], error.error["error_code"], error.error.arguments);
            if (callback) {
              callback();
            }
          }
        }
      );

      return requestObservable;
    } catch (error) {
      this.appDataService.updateShowLoadingPanel(false);
      return of('Failure');
    }
  }

  formatReceipt(receipt: string): string {
    if (!receipt || receipt.length !== 16) {
      return '';
    }

    return (
      receipt.substring(0, 4) + " " +
      receipt.substring(4, 8) + " " +
      receipt.substring(8, 12) + " " +
      receipt.substring(12, 16)
    );
  }

  public getHeader(confirmation?: string): HttpHeaders {
    let headers = new HttpHeaders();

    if (this.session) {
      headers = headers.set('X-Session', this.session.id);
      headers = headers.set('Accept-Language', 'en');
    }

    if (confirmation) {
      headers = headers.set('X-Confirmation', confirmation);
    }

    return headers;
  }

  logout(callback?: () => void) {
    const requestObservable = this.httpService.requestDeleteUserSession();
    requestObservable.subscribe(
      {
        next: () => {
          this.reset();
	  this.deleteSession();

          if (callback) {
            callback();
          }
        }
      }
    );
  };

}
