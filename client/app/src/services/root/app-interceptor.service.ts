import {Injectable, inject} from "@angular/core";
import {
  HttpInterceptor,
  HttpEvent,
  HttpRequest,
  HttpHandler,
  HttpClient,
  HttpErrorResponse,
  HttpResponse,
} from "@angular/common/http";
import {catchError, finalize, from, Observable, switchMap, tap, throwError} from "rxjs";
import {TokenResponse} from "@app/models/authentication/token-response";
import {CryptoService} from "@app/shared/services/crypto.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {AppDataService} from "@app/app-data.service";
import {RenderSchedulerService} from "@app/shared/services/render-scheduler.service";
import {ErrorCodes} from "@app/models/app/error-code";
import {of} from 'rxjs';
import {timer} from 'rxjs';

const protectedUrls = [
  "api/wizard",
  "api/auth/authentication",
  "api/auth/type",
  "api/auth/tokenauth",
  "api/user/reset/password",
  "api/recipient/rtip",
  "api/support"
];

@Injectable()
export class appInterceptor implements HttpInterceptor {
  private authenticationService = inject(AuthenticationService);
  private httpClient = inject(HttpClient);
  private cryptoService = inject(CryptoService);

  /**
   * A proof of work protects the endpoints reachable without authentication;
   * a user already identified by its session is not asked for it when it
   * opens a support request.
   */
  private requiresProofOfWork(url: string): boolean {
    const session = this.authenticationService.session;

    if (url.includes("api/signup")) {
      return true;
    }

    if (url.endsWith("api/auth/receiptauth")) {
      return !session;
    }

    if (url === "api/support") {
      return !session || session.role === "whistleblower";
    }

    return protectedUrls.includes(url);
  }

  private getAcceptLanguageHeader(): string | null {
    const language = sessionStorage.getItem("language");
    if (language) {
      return language;
    } else {
      const url = window.location.href;
      const hashFragment = url.split("#")[1];

      if (hashFragment && hashFragment.includes("lang=")) {
        return hashFragment.split("lang=")[1].split("&")[0];
      } else {
        return "";
      }
    }
  }

  private computeHtu(url: string): string {
    let path: string;
    try {
      if (/^https?:\/\//i.test(url)) {
        path = new URL(url).pathname;
      } else {
        path = "/" + url.replace(/^\/+/, "");
      }
    } catch {
      path = "/" + url.replace(/^\/+/, "");
    }

    path = path.split("?")[0].split("#")[0];

    // Strip the tenant prefix that the backend removes from request.path before
    // it computes the htu, so that the htu matches on both sides.
    path = path.replace(/^\/t\/[^/]+/, "");

    if (!path.startsWith("/")) {
      path = "/" + path;
    }

    // The DPoP proof binds only method + path, not scheme/host: GlobaLeaks is
    // frequently served behind proxies that rewrite the origin the backend sees,
    // and the session is already bound to a tenant server-side, so the path
    // alone is what both sides can agree on.
    return path;
  }

  private attachDpop(request: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    const session = this.authenticationService.session;

    const proof = this.cryptoService.generateDpopProof(
      request.method,
      this.computeHtu(request.url),
      session ? session.id : undefined
    );

    return from(proof).pipe(
      switchMap((dpop) => next.handle(request.clone({headers: request.headers.set("DPoP", dpop)})).pipe(
        tap((event) => {
          // Keep the DPoP proof clock aligned to the server regardless of the
          // device clock by learning the offset from the response Date header.
          if (event instanceof HttpResponse) {
            const date = event.headers.get("Date");
            if (date) {
              this.cryptoService.updateTimeOffset(Date.parse(date));
            }
          }
        })
      ))
    );
  }

  intercept(httpRequest: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    if (new URL(httpRequest.url, window.location.origin).origin !== window.location.origin) {
      return next.handle(httpRequest); // skip header injection
    }

    if (httpRequest.url.endsWith("/data/i18n/.json")) {
      return next.handle(httpRequest);
    }

    const authHeader = this.authenticationService.getHeader();
    let authRequest = httpRequest;

    authHeader.keys().forEach(header => {
      const headerValue = authHeader.get(header);
      if (headerValue) {
        authRequest = authRequest.clone({headers: authRequest.headers.set(header, headerValue)});
      }
    });

    authRequest = authRequest.clone({
      headers: authRequest.headers.set("Accept-Language", this.getAcceptLanguageHeader() || ""),
    });
    if (this.requiresProofOfWork(httpRequest.url)) {
      return this.httpClient.post("api/auth/token", {}).pipe(
        switchMap((response) =>
          from(this.cryptoService.proofOfWork(Object.assign(new TokenResponse(), response))).pipe(
            switchMap((ans) => this.attachDpop(httpRequest.clone({
              headers: httpRequest.headers.set("x-token", `${Object.assign(new TokenResponse(), response).id}:${ans}`)
                .set("Accept-Language", this.getAcceptLanguageHeader() || ""),
            }), next))
          )
        )
      );
    } else {
      return this.attachDpop(authRequest, next);
    }
  }
}

@Injectable()
export class ErrorCatchingInterceptor implements HttpInterceptor {
  private authenticationService = inject(AuthenticationService);
  private appDataService = inject(AppDataService);


  intercept(request: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {

    return next.handle(request)
      .pipe(
        catchError((error: HttpErrorResponse) => {
          if(error.error){
            // A resource not found is answered to the caller, which knows what its absence means
            if (error.error["error_code"] === 10) {
              this.authenticationService.deleteSession();
            }
            this.appDataService.errorCodes = new ErrorCodes(error.error["error_message"], error.error["error_code"], error.error["arguments"]);
          }
          return throwError(() => error);
        })
      );
  }
}

@Injectable()
export class CompletedInterceptor implements HttpInterceptor {
  private appDataService = inject(AppDataService);
  private renderScheduler = inject(RenderSchedulerService);

  count = 0;

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    if (!req.url.includes("api/auth/")) {
      this.count++;
      this.appDataService.updateShowLoadingPanel(true);
    }

    return next.handle(req).pipe(
      // Zoneless: the subscriber that consumes this response mutates component
      // state synchronously when the event is delivered; request a rendering
      // pass right after it so the result is shown without depending on any
      // later, unrelated trigger (a click, the loader timer, ...).
      tap({
        next: (event) => {
          if (event instanceof HttpResponse) {
            this.renderScheduler.schedule();
          }
        },
        error: () => this.renderScheduler.schedule()
      }),
      finalize(() => {
        if (!req.url.includes("api/auth/")) {
          if (this.count > 0) {
            this.count--;
	  }

          if (this.count === 0) {
            timer(100).pipe(
              switchMap(() => {
                this.appDataService.updateShowLoadingPanel(false);
                return of(null);
              })
            ).subscribe();
          }
        }
      })
    );
  }
}
