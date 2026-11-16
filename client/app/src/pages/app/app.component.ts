import {AfterViewInit, Component, HostListener, OnInit, Renderer2, inject, signal} from "@angular/core";
import {RenderSchedulerService} from "@app/shared/services/render-scheduler.service";
import {SessionActivityService} from "@app/services/helper/session-activity.service";
import {AppConfigService} from "@app/services/root/app-config.service";
import {AppDataService} from "@app/app-data.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {TrustedTypesService} from "@app/services/helper/trusted-types.service";
import {TranslateService, TranslatePipe} from "@ngx-translate/core";
import {NavigationEnd, Router, RouterOutlet} from "@angular/router";
import {BrowserCheckService} from "@app/shared/services/browser-check.service";
import {DOCUMENT, NgTemplateOutlet} from "@angular/common";
import {LiveAnnouncer} from "@angular/cdk/a11y";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {HeaderComponent} from "@app/shared/partials/header/header.component";
import {FooterComponent} from "@app/shared/partials/footer/footer.component";
import {PrivacyBadgeComponent} from "@app/shared/partials/privacybadge/privacy-badge.component";
import {DemoComponent} from "@app/shared/partials/demo/demo.component";
import {MessageConsoleComponent} from "@app/shared/partials/messageconsole/message-console.component";
import {AdminSidebarComponent} from "../admin/sidebar/sidebar.component";
import {AnalystSidebarComponent} from "../analyst/sidebar/sidebar.component";
import {CustodianSidebarComponent} from "../custodian/sidebar/sidebar.component";
import {ReceiptSidebarComponent} from "../recipient/sidebar/sidebar.component";
import {registerLocales, localeToBcp47} from "@app/services/helper/locale-provider";
import {mockEngine} from "@app/services/helper/mocks";
import {BodyDomObserverService} from "@app/shared/services/body-dom-observer.service";
import {WbTipResolver} from "@app/shared/resolvers/wb-tip-resolver.service";
import DOMPurify from 'dompurify';

registerLocales();

declare global {
  interface Window {
    GL: {
      language: string;
      mockEngine: any;
    };
  }
}
window.GL = {
  language: 'en', // Assuming a default language
  mockEngine: mockEngine
};

@Component({
    selector: "app-root",
    templateUrl: "./app.component.html",
    standalone: true,
    imports: [HeaderComponent, PrivacyBadgeComponent, AdminSidebarComponent, AnalystSidebarComponent, MessageConsoleComponent, DemoComponent, CustodianSidebarComponent, ReceiptSidebarComponent, FooterComponent, NgTemplateOutlet, RouterOutlet, TranslatePipe]
})
export class AppComponent implements AfterViewInit, OnInit {
  private renderScheduler = inject(RenderSchedulerService);
  private document = inject<Document>(DOCUMENT);
  private renderer = inject(Renderer2);
  protected browserCheckService = inject(BrowserCheckService);
  private router = inject(Router);
  protected translate = inject(TranslateService);
  protected appConfig = inject(AppConfigService);
  protected appDataService = inject(AppDataService);
  protected utilsService = inject(UtilsService);
  protected authenticationService = inject(AuthenticationService);
  private sessionActivity = inject(SessionActivityService);
  private bodyDomObserver = inject(BodyDomObserverService);
  private TrustedTypesService = inject(TrustedTypesService);
  private wbTipResolver = inject(WbTipResolver);
  private liveAnnouncer = inject(LiveAnnouncer);

  showSidebar = true;
  private announcedUrl = "";
  // On a phone the navigation is in the menu of the header, before the links of the session, and not a column
  readonly isPhone = signal(false);
  showLoadingPanel = true;
  supportedBrowser = true;
  loading = false;

  constructor() {
    const phone = this.document.defaultView?.matchMedia("(width < 768px)");
    if (phone) {
      this.isPhone.set(phone.matches);
      phone.addEventListener("change", (event) => this.isPhone.set(event.matches));
    }
    (window as any).scope = this.appDataService;
  }

  watchLanguage() {
    this.translate.onLangChange.subscribe(() => {
      document.getElementsByTagName("html")[0].setAttribute("lang", localeToBcp47(this.translate.getCurrentLang() ?? ""));
    });
  }

  checkToShowSidebar() {
    this.router.events.subscribe((event:any) => {
      if (event instanceof NavigationEnd) {
        const excludedUrls = [
          "/recipient/reports"
        ];
        const currentUrl = event.url;
        this.showSidebar = !excludedUrls.includes(currentUrl);
        this.announceNavigation(event.urlAfterRedirects);
      }
    });
  }

  // After a change of page a screen reader is told the title of the new one, and the focus, when
  // it was on something the change took away, goes to the content. Not on the first page, which
  // the browser announces by itself, nor when a page is read again through the blank route.
  private announceNavigation(url: string) {
    if (url === "/blank" || url === this.announcedUrl) {
      return;
    }

    const first = this.announcedUrl === "";
    this.announcedUrl = url;
    if (first) {
      return;
    }

    setTimeout(() => {
      this.liveAnnouncer.announce(this.document.title, "polite");

      const active = this.document.activeElement;
      if (!active || active === this.document.body) {
        this.document.getElementById("Content")?.focus({preventScroll: true});
      }
    });
  }

  // The link that skips to the content moves the focus there: as a plain anchor it would be a
  // route for the router of the hash
  skipToContent(event: Event) {
    event.preventDefault();
    this.document.getElementById("Content")?.focus();
  }

  ngOnInit() {
    DOMPurify.addHook('afterSanitizeAttributes', function (node) {
      // ensure any link always contain target _blank and rel noopener
      node.setAttribute('target', '_blank');
      node.setAttribute('rel', 'noopener');
    });

    this.appConfig.routeChangeListener();
    this.checkToShowSidebar();
  }

  public ngAfterViewInit(): void {
    this.sessionActivity.start();
    this.watchLanguage();

    this.appDataService.showLoadingPanel$.subscribe((value:any) => {
      this.showLoadingPanel = value;
      this.supportedBrowser = this.browserCheckService.checkBrowserSupport();
      this.renderScheduler.schedule();
    });

    requestIdleCallback(() => {
      let elem;
      elem = document.createElement("link");
      elem.rel = "stylesheet";
      elem.href = "css/fonts.css";
      document.head.appendChild(elem);

      elem = document.createElement("link");
      elem.rel = "stylesheet";
      elem.href = "s/css";
      document.head.appendChild(elem);

      elem = document.createElement("script");
      elem.type = "module";
      let scriptURL = "/s/script";
      if ((window as any).trustedTypes?.defaultPolicy) {
          const safeURL = (window as any).trustedTypes.defaultPolicy.createScriptURL(scriptURL);
          if (typeof safeURL === "string") {
              scriptURL = safeURL;
          }
      }
      elem.src = scriptURL;
      document.body.appendChild(elem);
    });
  }

  @HostListener('document:keydown', ['$event'])
  handleKeyDown(event: KeyboardEvent): void {
    if (event.key === 'F5') {
      event.preventDefault();
      // Drop the cached whistleblower tip so the resolver refetches it on reload;
      // recipient routes refetch on their own (component ngOnInit) and ignore this.
      this.wbTipResolver.dataModel = undefined;
      this.utilsService.reloadCurrentRoute();
    }
  }



  protected readonly location = location;
}
