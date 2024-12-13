import {ChangeDetectorRef, Component} from "@angular/core";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {AppConfigService} from "@app/services/root/app-config.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {AppDataService} from "@app/app-data.service";
import {TranslationService} from "@app/services/helper/translation.service";
import {HttpService} from "@app/shared/services/http.service";
import {ActivatedRoute, Router} from "@angular/router";

@Component({
  selector: "views-user",
  templateUrl: "./user.component.html"
})
export class UserComponent {
  private lastLang: string | null = null;

  constructor(protected activatedRoute: ActivatedRoute, protected httpService: HttpService, protected appConfigService: AppConfigService, private cdr: ChangeDetectorRef, protected authentication: AuthenticationService, protected preferences: PreferenceResolver, protected utils: UtilsService, protected appDataService: AppDataService, protected translationService: TranslationService, private router: Router) {
    this.onQueryParameterChangeListener();
  }

  onQueryParameterChangeListener() {
    this.activatedRoute.queryParams.subscribe(params => {
      const currentLang = params['lang'];
      const isSubmissionRoute = this.router.url.includes('/submission');
      const storageLanguage = sessionStorage.getItem("default_language");
      const languagesEnabled = this.appDataService.public.node.languages_enabled;

      if (currentLang && languagesEnabled.includes(currentLang)) {
        if (isSubmissionRoute && this.lastLang && this.lastLang !== currentLang) {
          location.reload();
        }
        else if (storageLanguage !== currentLang) {
          this.translationService.onChange(currentLang);
          sessionStorage.setItem("default_language", currentLang);
          if (!isSubmissionRoute) {
            this.appConfigService.reinit(true);
            this.utils.reloadCurrentRouteFresh();
          }
        }
      }
      this.lastLang = currentLang;
    });
  }

  onLogout(event: Event) {
    event.preventDefault();
    const promise = () => {
      sessionStorage.removeItem("default_language");
      this.translationService.onChange(this.appDataService.public.node.default_language);
      this.appConfigService.reinit(false);
      this.appConfigService.onValidateInitialConfiguration();
    };


    if(this.appDataService.page === 'accreditation-request' && this.appDataService.public.proxy_idp_enabled){
      window.location.href='/logout';
    }     
    else{
      this.authentication.logout(promise);
    }
      
  }

  onChangeLanguage() {
    this.cdr.detectChanges();
    sessionStorage.removeItem("default_language");
    this.translationService.onChange(this.translationService.language);
    this.appConfigService.reinit(false);
    this.utils.reloadCurrentRouteFresh(true);
  }
}
