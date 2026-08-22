import {AfterViewInit, Component, HostListener, OnInit, Renderer2, inject} from "@angular/core";
import {RenderSchedulerService} from "@app/shared/services/render-scheduler.service";
import {SessionActivityService} from "@app/services/helper/session-activity.service";
import {AppConfigService} from "@app/services/root/app-config.service";
import {AppDataService} from "@app/app-data.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {TrustedTypesService} from "@app/services/helper/trusted-types.service";
import {LangChangeEvent, TranslateService, TranslateModule} from "@ngx-translate/core";
import {NavigationEnd, Router, RouterOutlet} from "@angular/router";
import {BrowserCheckService} from "@app/shared/services/browser-check.service";
import {DOCUMENT} from "@angular/common";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {HeaderComponent} from "@app/shared/partials/header/header.component";
import {NgbCollapse} from "@ng-bootstrap/ng-bootstrap";
import {FooterComponent} from "@app/shared/partials/footer/footer.component";
import {PrivacyBadgeComponent} from "@app/shared/partials/privacybadge/privacy-badge.component";
import {DemoComponent} from "@app/shared/partials/demo/demo.component";
import {MessageConsoleComponent} from "@app/shared/partials/messageconsole/message-console.component";
import {OperationComponent} from "@app/shared/partials/operation/operation.component";
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
    imports: [HeaderComponent, PrivacyBadgeComponent, AdminSidebarComponent, AnalystSidebarComponent, MessageConsoleComponent, DemoComponent, OperationComponent, CustodianSidebarComponent, ReceiptSidebarComponent, FooterComponent, NgbCollapse, RouterOutlet, TranslateModule]
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

  showSidebar = true;
  isNavCollapsed = true;
  showLoadingPanel = true;
  supportedBrowser = true;
  loading = false;

  constructor() {
    (window as any).scope = this.appDataService;
  }

  watchLanguage() {
    this.translate.onLangChange.subscribe((event: LangChangeEvent) => {
      document.getElementsByTagName("html")[0].setAttribute("lang", localeToBcp47(this.translate.currentLang));
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
      }
    });
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
