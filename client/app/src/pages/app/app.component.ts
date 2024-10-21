import { AfterViewInit, ChangeDetectorRef, Component, HostListener, OnDestroy, OnInit, Renderer2, inject } from "@angular/core";
import {AppConfigService} from "@app/services/root/app-config.service";
import {AppDataService} from "@app/app-data.service";
import {UtilsService} from "@app/shared/services/utils.service";
import { LangChangeEvent, TranslateService, TranslateModule } from "@ngx-translate/core";
import { NavigationEnd, Router, RouterOutlet } from "@angular/router";
import {BrowserCheckService} from "@app/shared/services/browser-check.service";
import {animate, state, style, transition, trigger} from "@angular/animations";
import {TranslationService} from "@app/services/helper/translation.service";
import { DOCUMENT, NgClass } from "@angular/common";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import { HeaderComponent } from "../../shared/partials/header/header.component";
import { NgbCollapse } from "@ng-bootstrap/ng-bootstrap";
import { TranslatorPipe } from "../../shared/pipes/translate";
import { FooterComponent } from "@app/shared/partials/footer/footer.component";
import { PrivacyBadgeComponent } from "@app/shared/partials/privacybadge/privacy-badge.component";
import { DemoComponent } from "@app/shared/partials/demo/demo.component";
import { MessageConsoleComponent } from "@app/shared/partials/messageconsole/message-console.component";
import { OperationComponent } from "@app/shared/partials/operation/operation.component";
import { AdminSidebarComponent } from "../admin/sidebar/sidebar.component";
import { AnalystSidebarComponent } from "../analyst/sidebar/sidebar.component";
import { CustodianSidebarComponent } from "../custodian/sidebar/sidebar.component";
import { ReceiptSidebarComponent } from "../recipient/sidebar/sidebar.component";
import { HttpClient } from "@angular/common/http";
import { registerLocales } from "@app/services/helper/locale-provider";
import { mockEngine } from "@app/services/helper/mocks";
import { TranslateHttpLoader } from "@ngx-translate/http-loader";
import { DEFAULT_INTERRUPTSOURCES, Idle } from "@ng-idle/core";
import { CryptoService } from "@app/shared/services/crypto.service";
import { HttpService } from "@app/shared/services/http.service";
import { Keepalive } from "@ng-idle/keepalive";
registerLocales();

export function createTranslateLoader(http: HttpClient) {
  return new TranslateHttpLoader(http, "l10n/", "");
}

(window as any).mockEngine = mockEngine;
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
    animations: [
        trigger('fadeInOut', [
            state('void', style({
                opacity: 0
            })),
            transition(':enter, :leave', animate(150)),
        ])
    ],
    standalone: true,
    imports: [NgClass, HeaderComponent, PrivacyBadgeComponent, AdminSidebarComponent, AnalystSidebarComponent, MessageConsoleComponent, DemoComponent, OperationComponent, CustodianSidebarComponent, ReceiptSidebarComponent, FooterComponent, NgbCollapse, RouterOutlet, TranslateModule, TranslatorPipe]
})
export class AppComponent implements AfterViewInit, OnInit, OnDestroy{
  private document = inject<Document>(DOCUMENT);
  private renderer = inject(Renderer2);
  protected browserCheckService = inject(BrowserCheckService);
  private changeDetectorRef = inject(ChangeDetectorRef);
  private router = inject(Router);
  protected translationService = inject(TranslationService);
  protected translate = inject(TranslateService);
  protected appConfig = inject(AppConfigService);
  protected appDataService = inject(AppDataService);
  protected utilsService = inject(UtilsService);
  protected authenticationService = inject(AuthenticationService);
  private cryptoService = inject(CryptoService);
  private idle = inject(Idle);
  private keepalive = inject(Keepalive);
  private httpService = inject(HttpService);

  showSidebar: boolean = true;
  isNavCollapsed: boolean = true;
  showLoadingPanel = false;
  supportedBrowser = true;
  loading = false;


  constructor() {
    this.initIdleState();
    this.watchLanguage();
    (window as any).scope = this.appDataService;
  }

  watchLanguage() {
    this.translate.onLangChange.subscribe((event: LangChangeEvent) => {
      document.getElementsByTagName("html")[0].setAttribute("lang", this.translate.currentLang);
      this.translationService.handleLTRandRTLStyling(event, this.renderer);
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
    this.appConfig.routeChangeListener();
    this.checkToShowSidebar();
  }

  isWhistleblowerPage(): boolean {
    const currentHash = location.hash;
    return currentHash === "#/" || currentHash === "#/submission";
  }
  

  public ngAfterViewInit(): void {
    this.appDataService.showLoadingPanel$.subscribe((value:any) => {
      this.showLoadingPanel = value;
      this.supportedBrowser = this.browserCheckService.checkBrowserSupport();
      this.changeDetectorRef.detectChanges();
    });
  }

  @HostListener("window:beforeunload")
  async ngOnDestroy() {
    this.reset();
  }

  initIdleState() {
    this.idle.setIdle(1500);
    this.idle.setTimeout(300);
    this.keepalive.interval(30);
    this.idle.setInterrupts(DEFAULT_INTERRUPTSOURCES);

    this.keepalive.onPing.subscribe(() => {
      if (this.authenticationService && this.authenticationService.session) {
        const token = this.authenticationService.session.token;
        this.cryptoService.proofOfWork(token.id).subscribe((result:any) => {
	  const param = {'token': token.id + ":" + result};
          this.httpService.requestRefreshUserSession(param).subscribe(((result:any) => {
            this.authenticationService.session.token = result.token;
	  }));
	});
      }
    });

    this.idle.onTimeout.subscribe(() => {
      if (this.authenticationService && this.authenticationService.session) {
        if (this.authenticationService.session.role === "whistleblower") {
          window.location.replace("about:blank");
        } else {
          this.authenticationService.deleteSession();
          this.authenticationService.loginRedirect();
        }
      }
    });

    this.reset();
  }

  reset() {
    this.idle.watch();
    this.authenticationService.reset();
  }

  protected readonly location = location;
}
