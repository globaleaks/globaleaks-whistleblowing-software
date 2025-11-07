import {AfterViewInit, ChangeDetectorRef, Component, HostListener, OnDestroy, OnInit, Renderer2, inject} from "@angular/core";
import {AppConfigService} from "@app/services/root/app-config.service";
import {AppDataService} from "@app/app-data.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {TrustedTypesService} from "@app/services/helper/trusted-types.service";
import {LangChangeEvent, TranslateService, TranslateModule} from "@ngx-translate/core";
import {NavigationEnd, Router, RouterOutlet} from "@angular/router";
import {BrowserCheckService} from "@app/shared/services/browser-check.service";
import {DOCUMENT, NgClass} from "@angular/common";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {HeaderComponent} from "@app/shared/partials/header/header.component";
import {NgbCollapse} from "@ng-bootstrap/ng-bootstrap";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {FooterComponent} from "@app/shared/partials/footer/footer.component";
import {PrivacyBadgeComponent} from "@app/shared/partials/privacybadge/privacy-badge.component";
import {DemoComponent} from "@app/shared/partials/demo/demo.component";
import {MessageConsoleComponent} from "@app/shared/partials/messageconsole/message-console.component";
import {OperationComponent} from "@app/shared/partials/operation/operation.component";
import {AdminSidebarComponent} from "../admin/sidebar/sidebar.component";
import {AnalystSidebarComponent} from "../analyst/sidebar/sidebar.component";
import {CustodianSidebarComponent} from "../custodian/sidebar/sidebar.component";
import {ReceiptSidebarComponent} from "../recipient/sidebar/sidebar.component";
import {HttpClient} from "@angular/common/http";
import {registerLocales} from "@app/services/helper/locale-provider";
import {mockEngine} from "@app/services/helper/mocks";
import {DEFAULT_INTERRUPTSOURCES, Idle} from "@ng-idle/core";
import {CryptoService} from "@app/shared/services/crypto.service";
import {HttpService} from "@app/shared/services/http.service";
import {BodyDomObserverService} from "@app/shared/services/body-dom-observer.service";
import {Keepalive} from "@ng-idle/keepalive";
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
    imports: [NgClass, HeaderComponent, PrivacyBadgeComponent, AdminSidebarComponent, AnalystSidebarComponent, MessageConsoleComponent, DemoComponent, OperationComponent, CustodianSidebarComponent, ReceiptSidebarComponent, FooterComponent, NgbCollapse, RouterOutlet, TranslateModule, TranslatorPipe]
})
export class AppComponent implements AfterViewInit, OnInit, OnDestroy{
  private document = inject<Document>(DOCUMENT);
  private renderer = inject(Renderer2);
  protected browserCheckService = inject(BrowserCheckService);
  private changeDetectorRef = inject(ChangeDetectorRef);
  private router = inject(Router);
  protected translate = inject(TranslateService);
  protected appConfig = inject(AppConfigService);
  protected appDataService = inject(AppDataService);
  protected utilsService = inject(UtilsService);
  protected authenticationService = inject(AuthenticationService);
  private cryptoService = inject(CryptoService);
  private idle = inject(Idle);
  private keepalive = inject(Keepalive);
  private httpService = inject(HttpService);
  private bodyDomObserver = inject(BodyDomObserverService);
  private TrustedTypesService = inject(TrustedTypesService);

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
      document.getElementsByTagName("html")[0].setAttribute("lang", this.translate.currentLang);
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
    this.initIdleState();
    this.watchLanguage();

    this.appDataService.showLoadingPanel$.subscribe((value:any) => {
      this.showLoadingPanel = value;
      this.supportedBrowser = this.browserCheckService.checkBrowserSupport();
      this.changeDetectorRef.detectChanges();
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
      this.utilsService.reloadCurrentRoute();
    }
  }

  @HostListener("window:beforeunload")
  async ngOnDestroy() {
    this.reset();
  }

  initIdleState() {
    this.idle.setIdle(1800);
    this.idle.setTimeout(false);
    this.keepalive.interval(30);
    this.idle.setInterrupts(DEFAULT_INTERRUPTSOURCES);

    this.keepalive.onPing.subscribe(() => {
      if (this.authenticationService.session) {
        const token = this.authenticationService.session.token;
        this.cryptoService.proofOfWork(token).subscribe((result:any) => {
	  const param = {'token': token.id + ":" + result};
          this.httpService.requestRefreshUserSession(param).subscribe(((result:any) => {
            this.authenticationService.session.token = result.token;
	  }));
	});
      }
    });

    this.idle.onIdleStart.subscribe(() => {
      this.authenticationService.deleteSession();
    });

    this.reset();
  }

  reset() {
    this.idle.watch();
  }

  protected readonly location = location;
}
