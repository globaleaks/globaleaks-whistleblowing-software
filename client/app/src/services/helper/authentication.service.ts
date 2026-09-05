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
import {HttpErrorResponse, HttpHeaders} from "@angular/common/http";
import {NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {OtkcAccessComponent} from "@app/shared/modals/otkc-access/otkc-access.component";
import {DomSanitizer} from '@angular/platform-browser';
import {CryptoService} from "@app/shared/services/crypto.service";
import {OAuthService} from "angular-oauth2-oidc";
import {IdpService} from "@app/services/root/idp.service";

@Injectable({
  providedIn: "root"
})
export class AuthenticationService {
  private readonly modalService = inject(NgbModal);
  private readonly titleService = inject(TitleService);
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly httpService = inject(HttpService);
  private readonly appDataService = inject(AppDataService);
  private readonly router = inject(Router);
  private readonly sanitizer = inject(DomSanitizer);
  private readonly cryptoService = inject(CryptoService);
  private readonly oauthService = inject(OAuthService);
  private readonly idpService = inject(IdpService);

  public session: any = undefined;
  permissions: { can_upload_files: boolean }
  loginInProgress = false;
  requireAuthCode = false;
  requireUsername = false;
  loginData: LoginDataRef = new LoginDataRef();

  public reset() {
    this.loginInProgress = false;
    this.requireAuthCode = false;
    this.requireUsername = false;
    this.loginData = new LoginDataRef();
  };

  /**
   * Resolve the account bound to the identity authenticated on the identity
   * provider
   *
   * The account bound to the identity is resolved by the backend and presented
   * to its user, that is asked for its password alone; an identity not bound to
   * any account yet requires instead the user to identify the account that the
   * identity is going to be bound to on this first authentication, or is
   * provisioned an account of its own when the site is configured to do so.
   */
  async checkIdpBinding() {
    if (!this.appDataService.public.node.idp || !this.oauthService.hasValidIdToken()) {
      return;
    }

    try {
      const res = await firstValueFrom(this.httpService.requestAuthType(JSON.stringify({"username": ""}), this.getHeader()));

      // An identity for which an account is provisioned is authenticated by the
      // identity provider alone; its user is then required to set a password
      if (res.type === "provisioning") {
        this.requireUsername = false;
        this.loginData.loginUsername = "";
        await this.login(0, "", "", "");
        return;
      }

      this.requireUsername = res.type === "binding";
      this.loginData.loginUsername = res.username || "";
    } catch {
      this.requireUsername = true;
    }
  }

  /**
   * True when the identity authenticated on the identity provider is bound to
   * an account of the platform.
   *
   * The account is resolved by the backend from the identity itself, so a
   * request carrying the token of that identity is attributed to it even
   * before the password completes the login. An identity still to be bound
   * identifies no account, and whoever presents it is anybody.
   */
  get idpIdentityBound(): boolean {
    return !!this.appDataService.public.node.idp &&
      this.oauthService.hasValidIdToken() &&
      !this.requireUsername;
  }

  deleteSession() {
    const role = this.session ? this.session.role : 'recipient';
    this.session = null;
    if (role === "whistleblower") {
      window.location.replace("about:blank");
    } else {
      this.performLogout();
    }
  };

  private getTenantBasePath(): string {
    const path = window.location.pathname || "";
    const match = path.match(/^\/t\/[^/]+/);
    return match ? match[0] : "";
  }

  private performLogout() {
    if (this.appDataService.public.node.idp) {
      this.idpService.restartLogin();
      return;
    }
    const tenantBasePath = this.getTenantBasePath();
    const loginPath = tenantBasePath ? `${tenantBasePath}/#/login` : "/#/login";
    window.location.replace(loginPath);
  }

  setSession(response: Session) {
    this.session = response;
    if (this.appDataService.public.node.idp && this.oauthService.hasValidIdToken()) {
      this.idpService.setupAutomaticRefresh();
    }
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

            // An account bound to the identity is resolved by the backend via the identity; the
            // username only binds an unbound one
            if (this.appDataService.public.node.idp && username !== "whistleblower" && !this.requireUsername) {
              username = "";
            }

            const res = await firstValueFrom(this.httpService.requestAuthType(JSON.stringify({'username': username !== "whistleblower" ? username : ""}), username !== "whistleblower" ? authHeader : undefined));
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
               const role = ["receiver", "transmitter"].includes(response.role) ? "recipient" : response.role;
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
                this.httpService.requestWhistleblowerOperations({
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
                // A receipt was provided: a report exists and is the page to
                // reach
                this.titleService.setPage("tippage");
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
                let redirect = this.activatedRoute.snapshot.queryParams['redirect'] || '/';
                redirect = decodeURIComponent(redirect);

	        if (redirect !== "/") {
                  redirect = this.sanitizer.sanitize(SecurityContext.URL, redirect) || '';

                  // Honor only local redirects; a protocol relative one names
                  // another host and is not local
                  if (redirect.startsWith("/") && !redirect.startsWith("//")) {
                    // The destination may carry its own query string: it is
                    // navigated as a url and not as a single path segment
                    this.router.navigateByUrl(redirect);
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
    } catch {
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

    // The identity is attested by the ID token; the access token is a credential towards the APIs of
    // the IdP
    if (this.oauthService.hasValidIdToken()) {
      const token = this.oauthService.getIdToken();
      headers = headers.set('Authorization', `Bearer ${token}`);
    }

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
