import {Location} from "@angular/common";
import {Injectable, inject} from "@angular/core";
import {Router} from "@angular/router";
import {AppDataService} from "@app/app-data.service";
import {OAuthService, OAuthStorage} from "angular-oauth2-oidc";

class TenantOAuthStorage implements OAuthStorage {
  constructor(private prefix: string) {}

  getItem(key: string): string | null {
    return window.sessionStorage.getItem(this.prefix + key);
  }

  removeItem(key: string): void {
    window.sessionStorage.removeItem(this.prefix + key);
  }

  setItem(key: string, data: string): void {
    window.sessionStorage.setItem(this.prefix + key, data);
  }
}

@Injectable({
  providedIn: "root"
})
export class IdpService {
  private appDataService = inject(AppDataService);
  private location = inject(Location);
  private oauthService = inject(OAuthService);
  private router = inject(Router);

  private configurationKey = "";
  private initialization?: Promise<boolean>;
  private loginStarted = false;

  private getTenantBasePath(): string {
    const path = window.location.pathname || "";
    const match = path.match(/^\/t\/[^/]+/);
    return match ? match[0] : "";
  }

  private getTenantStoragePrefix(): string {
    return `oidc:${this.getTenantBasePath() || "root"}:`;
  }

  private getReturnRoute(routePath?: string): string {
    const route = routePath || this.location.path() || "/login";
    return route === "/signup" || route.startsWith("/signup?") ? route : "/login";
  }

  private configure() {
    const tenantBasePath = this.getTenantBasePath();

    this.oauthService.setStorage(new TenantOAuthStorage(this.getTenantStoragePrefix()));
    this.oauthService.configure({
      issuer: this.appDataService.public.node.idp_issuer,
      redirectUri: window.location.origin + tenantBasePath + "/#/login",
      clientId: "globaleaks",
      responseType: "code",
      scope: "openid profile email",
      requireHttps: false,
      postLogoutRedirectUri: window.location.origin + tenantBasePath + "/#/login"
    });
  }

  private restoreReturnRoute() {
    if (!this.oauthService.state) {
      return;
    }

    let route = this.oauthService.state;
    try {
      route = decodeURIComponent(route);
    } catch (_) {
      route = "/login";
    }

    this.oauthService.state = "";
    route = this.getReturnRoute(route);
    if (route.startsWith("/signup") && this.router.url !== route) {
      this.router.navigateByUrl(route, {replaceUrl: true}).then();
    }
  }

  initialize(): Promise<boolean> {
    if (!this.appDataService.public.node.idp) {
      return Promise.resolve(false);
    }

    const configurationKey = this.getTenantStoragePrefix() + this.appDataService.public.node.idp_issuer;
    if (configurationKey !== this.configurationKey) {
      if (this.configurationKey) {
        this.oauthService.logOut(true);
      }
      this.configurationKey = configurationKey;
      this.initialization = undefined;
      this.loginStarted = false;
      this.configure();
    }

    if (!this.initialization) {
      this.initialization = this.oauthService.loadDiscoveryDocumentAndTryLogin().then(() => {
        this.loginStarted = false;
        const authenticated = this.oauthService.hasValidAccessToken();
        if (authenticated) {
          this.restoreReturnRoute();
        }
        return authenticated;
      }).catch(error => {
        this.initialization = undefined;
        this.loginStarted = false;
        throw error;
      });
    }

    return this.initialization;
  }

  disable() {
    if (this.configurationKey) {
      this.oauthService.logOut(true);
    }
    this.configurationKey = "";
    this.initialization = undefined;
    this.loginStarted = false;
  }

  startLogin(routePath?: string): Promise<void> {
    const returnRoute = this.getReturnRoute(routePath);
    return this.initialize().then(() => {
      if (this.oauthService.hasValidAccessToken() || this.loginStarted) {
        return;
      }

      this.loginStarted = true;
      this.oauthService.initLoginFlow(returnRoute, {prompt: "login"});
    });
  }

  restartLogin(): Promise<void> {
    this.oauthService.logOut(true);
    this.loginStarted = false;
    return this.startLogin("/login");
  }

  setupAutomaticRefresh() {
    this.oauthService.setupAutomaticSilentRefresh();
  }
}
