import {Component, inject} from "@angular/core";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {AppConfigService} from "@app/services/root/app-config.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {AppDataService} from "@app/app-data.service";
import {TranslationService} from "@app/services/helper/translation.service";
import {HttpService} from "@app/shared/services/http.service";
import {ActivatedRoute, Router} from "@angular/router";
import {NgSelectComponent, NgOptionComponent, NgLabelTemplateDirective} from "@ng-select/ng-select";
import {FormsModule} from "@angular/forms";
import {ReceiptComponent} from "../../../receipt/receipt.component";
import {TranslatePipe} from "@ngx-translate/core";
import {OrderByPipe} from "@app/shared/pipes/order-by.pipe";
import {NgbDropdownModule, NgbTooltipModule} from '@ng-bootstrap/ng-bootstrap';
import {ThemeService} from "@app/shared/theme/theme.service";
import {NgTemplateOutlet} from "@angular/common";


@Component({
    selector: "src-user",
    templateUrl: "./user.component.html",
    standalone: true,
    imports: [NgbTooltipModule, NgbDropdownModule, NgTemplateOutlet, NgSelectComponent, FormsModule, NgOptionComponent, NgLabelTemplateDirective, ReceiptComponent, TranslatePipe, OrderByPipe]
})
export class UserComponent {
  protected activatedRoute = inject(ActivatedRoute);
  protected httpService = inject(HttpService);
  protected appConfigService = inject(AppConfigService);
  protected authentication = inject(AuthenticationService);
  protected preferences = inject(PreferenceResolver);
  protected utilsService = inject(UtilsService);
  protected appDataService = inject(AppDataService);
  protected translationService = inject(TranslationService);
  protected themeService = inject(ThemeService);
  private router = inject(Router);

  constructor() {
    this.onQueryParameterChangeListener();
  }

  // The name of a language in its own words and script, as the list of the languages tells it
  languageNative(code: string): string {
    const language = this.appDataService.languages_enabled_selector.find(l => l.code === code);
    return language ? language.native : code;
  }

  onChangeLanguage(language: string) {
    this.translationService.setLanguage(language);
    this.appConfigService.reload();
  }

  onQueryParameterChangeListener() {
    this.activatedRoute.queryParams.subscribe(params => {
      const storedLang = sessionStorage.getItem("language");
      const langParam = params['lang'];
      const languagesEnabled = this.appDataService.public.node.languages_enabled;

      if (langParam && languagesEnabled.includes(langParam)) {
        // The language of the URL may be already the one in use, as it is
        // preferred also on the first load: then it is enough to drop it
        const reload = langParam !== storedLang;

        sessionStorage.setItem("language", langParam);

        // Get current hash
        const hash = window.location.hash; // e.g., "#!/some/path?lang=en&foo=bar"

        // Split path and query
        const [path, query] = hash.split('?');

        // Remove the 'lang' param from the query if present
        const newQuery = query
          ? query
              .split('&')
              .filter(param => !param.startsWith('lang='))
              .join('&')
          : '';

        // Rebuild hash
        window.location.hash = newQuery ? `${path}?${newQuery}` : path;

        if (reload) {
          window.location.reload();
        }
      }
    });
  }

  onLogout(event: Event) {
    event.preventDefault();
    const promise = () => {
      this.appConfigService.reinit();
      this.appConfigService.onValidateInitialConfiguration();
    };

    this.authentication.logout(promise);
  }
}
