import {Location} from "@angular/common";
import {Injectable, inject} from "@angular/core";
import {Router} from "@angular/router";
import {AppDataService} from "@app/app-data.service";
import {OAuthService, OAuthStorage} from "angular-oauth2-oidc";

export type IdpContext = "login" | "signup";

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
  private storagePrefix = "";
  private initialization?: Promise<boolean>;
  private loginStarted = false;

  private getTenantBasePath(): string {
    const path = window.location.pathname || "";
    const match = path.match(/^\/t\/[^/]+/);
    return match ? match[0] : "";
  }

  private getTenantKeyPrefix(): string {
    return `oidc:${this.getTenantBasePath() || "root"}:`;
  }

  private getTenantStoragePrefix(context: IdpContext): string {
    const login = this.getContextConfig("login");
    const signup = this.getContextConfig("signup");

    // Signup tokens are kept apart only when the signup IdP differs from the one of the site
    if (context === "signup" && (!login.enabled || login.issuer !== signup.issuer || login.clientId !== signup.clientId)) {
      return this.getTenantKeyPrefix() + "signup:";
    }

    return this.getTenantKeyPrefix();
  }

  private getPendingContextKey(): string {
    return this.getTenantKeyPrefix() + "context";
  }

  private getPendingContext(): IdpContext | null {
    const context = window.sessionStorage.getItem(this.getPendingContextKey());
    return context === "signup" || context === "login" ? context : null;
  }

  private setPendingContext(context: IdpContext | null) {
    if (context) {
      window.sessionStorage.setItem(this.getPendingContextKey(), context);
    } else {
      window.sessionStorage.removeItem(this.getPendingContextKey());
    }
  }

  private getContextConfig(context: IdpContext): { enabled: boolean, issuer: string, clientId: string } {
    const node = this.appDataService.public.node;

    // The signup is authenticated against the IdP inherited from the profile
    // configured for the sites created via signup
    if (context === "signup") {
      return {enabled: !!node.signup_idp, issuer: node.signup_idp_issuer, clientId: node.signup_idp_client_id};
    }

    return {enabled: !!node.idp, issuer: node.idp_issuer, clientId: node.idp_client_id};
  }

  private getReturnRoute(routePath?: string): string {
    const route = routePath || this.location.path() || "/login";
    return route === "/signup" || route.startsWith("/signup?") ? route : "/login";
  }

  private configure(context: IdpContext, storagePrefix: string) {
    const tenantBasePath = this.getTenantBasePath();
    const config = this.getContextConfig(context);

    this.oauthService.setStorage(new TenantOAuthStorage(storagePrefix));
    this.oauthService.configure({
      issuer: config.issuer,
      redirectUri: window.location.origin + tenantBasePath + "/#/login",
      clientId: config.clientId,
      responseType: "code",
      scope: "openid profile email",
      // HTTPS required; plain HTTP only towards the loopback, mirroring the backend
      requireHttps: /^http:\/\/(localhost|127\.0\.0\.1|\[::1\])([:/]|$)/.test(config.issuer) ? false : true,
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

  private hasIdpResponse(): boolean {
    const url = window.location.href;
    return url.indexOf("code=") !== -1 && url.indexOf("state=") !== -1;
  }

  isSignupLoginPending(): boolean {
    return this.hasIdpResponse() && this.getPendingContext() === "signup";
  }

  initialize(context?: IdpContext): Promise<boolean> {
    // The authentication is always redirected back on the login route and is
    // therefore completed with the configuration of the context that started it
    const activeContext = context || (this.hasIdpResponse() ? this.getPendingContext() : null) || "login";
    const config = this.getContextConfig(activeContext);

    if (!config.enabled) {
      return Promise.resolve(false);
    }

    const storagePrefix = this.getTenantStoragePrefix(activeContext);
    const configurationKey = storagePrefix + config.issuer + ":" + config.clientId;
    if (configurationKey !== this.configurationKey) {
      // The tokens are dropped only when the IdP configured for the session in
      // use changes; sessions kept in a dedicated storage are left untouched
      if (this.configurationKey && this.storagePrefix === storagePrefix) {
        this.oauthService.logOut(true);
      }

      this.storagePrefix = storagePrefix;
      this.configurationKey = configurationKey;
      this.initialization = undefined;
      this.loginStarted = false;
      this.configure(activeContext, storagePrefix);
    }

    if (!this.initialization) {
      this.initialization = this.oauthService.loadDiscoveryDocumentAndTryLogin().then(() => {
        this.loginStarted = false;
        const authenticated = this.oauthService.hasValidIdToken();
        if (authenticated) {
          this.setPendingContext(null);
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
    this.storagePrefix = "";
    this.initialization = undefined;
    this.loginStarted = false;
    this.setPendingContext(null);
  }

  startLogin(routePath?: string, context: IdpContext = "login"): Promise<void> {
    const returnRoute = this.getReturnRoute(routePath);
    this.setPendingContext(context === "signup" ? "signup" : null);
    return this.initialize(context).then(() => {
      if (this.oauthService.hasValidIdToken() || this.loginStarted) {
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
