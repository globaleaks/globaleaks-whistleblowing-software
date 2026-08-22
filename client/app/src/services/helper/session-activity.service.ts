import {DOCUMENT} from "@angular/common";
import {Injectable, OnDestroy, inject} from "@angular/core";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {CryptoService} from "@app/shared/services/crypto.service";
import {HttpService} from "@app/shared/services/http.service";

/**
 * Keeps an authenticated session alive while the operator is active and
 * terminates it after a period of inactivity.
 *
 * Activity is any pointer, keyboard, touch or scroll event on the document.
 * Every KEEPALIVE_SECONDS the session token is refreshed; once no activity
 * has been observed for IDLE_SECONDS the session is deleted.
 */
@Injectable({
  providedIn: "root"
})
export class SessionActivityService implements OnDestroy {
  static readonly IDLE_SECONDS = 1800;
  static readonly KEEPALIVE_SECONDS = 30;

  private static readonly ACTIVITY_EVENTS = ["mousemove", "mousedown", "keydown", "wheel", "touchstart", "touchmove", "scroll"];

  private document = inject(DOCUMENT);
  private authenticationService = inject(AuthenticationService);
  private cryptoService = inject(CryptoService);
  private httpService = inject(HttpService);

  private lastActivity = Date.now();
  private timer: ReturnType<typeof setInterval> | null = null;
  private readonly onActivity = () => {
    this.lastActivity = Date.now();
  };

  start(): void {
    if (this.timer !== null) {
      return;
    }

    for (const event of SessionActivityService.ACTIVITY_EVENTS) {
      this.document.addEventListener(event, this.onActivity, {passive: true, capture: true});
    }

    this.timer = setInterval(() => this.tick(), SessionActivityService.KEEPALIVE_SECONDS * 1000);
  }

  private tick(): void {
    const session = this.authenticationService.session;

    if (!session) {
      return;
    }

    if (Date.now() - this.lastActivity >= SessionActivityService.IDLE_SECONDS * 1000) {
      this.authenticationService.deleteSession();
      return;
    }

    const token = session.token;

    this.cryptoService.proofOfWork(token).subscribe((answer: number) => {
      this.httpService.requestRefreshUserSession({"token": token.id + ":" + answer}).subscribe((response: any) => {
        if (this.authenticationService.session) {
          this.authenticationService.session.token = response.token;
        }
      });
    });
  }

  ngOnDestroy(): void {
    if (this.timer !== null) {
      clearInterval(this.timer);
      this.timer = null;
    }

    for (const event of SessionActivityService.ACTIVITY_EVENTS) {
      this.document.removeEventListener(event, this.onActivity, {capture: true});
    }
  }
}
