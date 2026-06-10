import {Location} from '@angular/common';
import {Injectable, inject} from "@angular/core";
import {HttpService} from "@app/shared/services/http.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {AppDataService} from "@app/app-data.service";
import {FieldUtilitiesService} from "@app/shared/services/field-utilities.service";
import {TranslationService} from "@app/services/helper/translation.service";
import {Router, NavigationEnd, ActivatedRoute} from "@angular/router";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {LanguagesSupported} from "@app/models/app/public-model";
import {TitleService} from "@app/shared/services/title.service";
import {NgZone} from "@angular/core";
import {Observable, forkJoin, of} from "rxjs";
import {map} from "rxjs/operators";

@Injectable({
  providedIn: "root"
})
export class AppConfigService {
  private location = inject(Location);
  private titleService = inject(TitleService);
  authenticationService = inject(AuthenticationService);
  private translationService = inject(TranslationService);
  private utilsService = inject(UtilsService);
  private router = inject(Router);
  private activatedRoute = inject(ActivatedRoute);
  private httpService = inject(HttpService);
  private appDataService = inject(AppDataService);
  private fieldUtilitiesService = inject(FieldUtilitiesService);
  private ngZone = inject(NgZone);
  private isRunning = false;

  public sidebar = "";

  constructor() {
    this.init();
  }

  init() {
    this.activatedRoute.paramMap.subscribe(_ => {
      this.localInitialization();
    });
  }

  public setHomepage() {
    location.replace("/");
  };

  public setPage(page: string) {
    this.appDataService.page = page;
    this.titleService.setTitle();
  };

  public localInitialization(languageInit = true, callback?: () => void) {
    this.httpService.getPublicResource().subscribe({
      next: data => {
        if (data.body !== null) {
          this.appDataService.updatePublic(data.body);
        }
        this.appDataService.contexts_by_id = this.utilsService.array_to_map(this.appDataService.public.contexts);
        this.appDataService.receivers_by_id = this.utilsService.array_to_map(this.appDataService.public.receivers);
        this.appDataService.questionnaires_by_id = this.utilsService.array_to_map(this.appDataService.public.questionnaires);
        this.appDataService.submissionStatuses = this.appDataService.public.submission_statuses;
        this.appDataService.submission_statuses_by_id = this.utilsService.array_to_map(this.appDataService.public.submission_statuses);

        for (const [key] of Object.entries(this.appDataService.questionnaires_by_id)) {
          this.registerQuestionnaire(this.appDataService.questionnaires_by_id[key]);
        }

        for (const [key] of Object.entries(this.appDataService.contexts_by_id)) {
          this.linkContextQuestionnaires(this.appDataService.contexts_by_id[key]);
        }

        this.appDataService.connection = {
          "tor": data.headers.get("X-Check-Tor") === "true" || location.host.match(/\.onion$/),
        };

        this.appDataService.privacy_badge_open = !this.appDataService.connection.tor;
        this.appDataService.languages_enabled = new Map<string, LanguagesSupported>();
        this.appDataService.languages_enabled_selector = [];
        this.appDataService.languages_supported = new Map<string, LanguagesSupported>();

        this.appDataService.public.node.languages_supported.forEach((lang: LanguagesSupported)=> {
          this.appDataService.languages_supported.set(lang.code, lang);

          if (this.appDataService.public.node.languages_enabled.includes(lang.code)) {
            this.appDataService.languages_enabled.set(lang.code, lang);
            this.appDataService.languages_enabled_selector.push(lang);
          }
        });

        this.translationService.setLanguage(sessionStorage.getItem("language") ||
                                            this.appDataService.public.node.default_language ||
                                            'en');

        this.titleService.setTitle();
        this.onValidateInitialConfiguration();

        if (callback) {
          callback();
        }
      }
    });
  }

  onValidateInitialConfiguration() {
    if (this.appDataService.public.node) {
      if (!this.appDataService.public.node.wizard_done) {
        location.replace("/#/wizard");
      } else if ((this.location.path() === "" || this.location.path() === "/submission") && !this.appDataService.public.node.enable_signup && this.appDataService.public.node.adminonly && !this.authenticationService.session) {
        location.replace("/#/login");
      } else if (this.location.path() === "" && this.appDataService.public.node.enable_signup && !location.href.endsWith("admin/home")) {
        location.replace("/#/signup");
      } else if (this.location.path() === "/signup" && !this.appDataService.public.node.enable_signup) {
        location.replace("/#/");
      } else if (this.appDataService.page === "blank") {
        this.appDataService.page = "homepage"
      }
    }
  }

  loadAdminRoute(newPath: string) {
    this.appDataService.public.node.wizard_done = true;
    this.appDataService.public.node.languages_enabled = [];
    this.appDataService.public.node.name = "Globaleaks";

    this.router.navigateByUrl(newPath).then(() => {
      this.sidebar = "admin-sidebar";
      this.titleService.setTitle();
    });
  }

  routeChangeListener() {
    this.router.events.subscribe((event) => {
      if (event instanceof NavigationEnd) {
        this.onValidateInitialConfiguration();
        const lastChildRoute = this.findLastChildRoute(this.router.routerState.root);
        if (lastChildRoute && lastChildRoute.snapshot.data && lastChildRoute.snapshot.data["pageTitle"]) {
          this.appDataService.header_title = lastChildRoute.snapshot.data["pageTitle"];
          this.sidebar = lastChildRoute.snapshot.data["sidebar"];
          this.titleService.setTitle();
        } else {
          this.appDataService.header_title = "";
          this.sidebar = "";
          this.titleService.setTitle();
        }
      }
    });
  }

  findLastChildRoute(route: ActivatedRoute): ActivatedRoute {
    while (route.firstChild) {
      route = route.firstChild;
    }
    return route;
  }

  private registerQuestionnaire(questionnaire: any) {
    this.fieldUtilitiesService.parseQuestionnaire(questionnaire, {
      fields: [],
      fields_by_id: {},
      options_by_id: {}
    });
    questionnaire.steps = questionnaire.steps.sort((a: { order: number; }, b: { order: number; }) => a.order > b.order);
    this.appDataService.questionnaires_by_id[questionnaire.id] = questionnaire;
  }

  private linkContextQuestionnaires(context: any) {
    context.questionnaire = this.appDataService.questionnaires_by_id[context.questionnaire_id];
    if (context.additional_questionnaire_id) {
      context.additional_questionnaire = this.appDataService.questionnaires_by_id[context.additional_questionnaire_id];
    }
  }

  loadContext(id: string): Observable<any> {
    const existing = this.appDataService.contexts_by_id[id];
    if (existing) {
      return of(existing);
    }

    return this.httpService.getPublicContextResource(id).pipe(
      map(data => {
        for (const questionnaire of data.questionnaires) {
          this.registerQuestionnaire(questionnaire);
        }

        this.linkContextQuestionnaires(data.context);
        this.appDataService.contexts_by_id[data.context.id] = data.context;

        return data.context;
      })
    );
  }

  loadContexts(ids: string[]): Observable<any[]> {
    const missing = Array.from(new Set(ids)).filter(id => id && !this.appDataService.contexts_by_id[id]);
    if (missing.length === 0) {
      return of([]);
    }

    return forkJoin(missing.map(id => this.loadContext(id)));
  }

  reinit(languageInit = true) {
    this.localInitialization(languageInit);
  }

  reload() {
    this.localInitialization(true, () => {
      const url = this.router.url;
      this.router.navigateByUrl('/blank', {skipLocationChange: true}).then(() => {
        this.router.navigateByUrl(url);
      });
    });
  }
}
