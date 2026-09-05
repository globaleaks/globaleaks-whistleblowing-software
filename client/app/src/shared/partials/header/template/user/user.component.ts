import {Component, inject} from "@angular/core";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {AppConfigService} from "@app/services/root/app-config.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {AppDataService} from "@app/app-data.service";
import {TranslationService} from "@app/services/helper/translation.service";
import {HttpService} from "@app/shared/services/http.service";
import {ActivatedRoute} from "@angular/router";
import {NgSelectComponent, NgOptionComponent} from "@ng-select/ng-select";
import {FormsModule} from "@angular/forms";
import {ReceiptComponent} from "../../../receipt/receipt.component";
import {TranslateModule} from "@ngx-translate/core";
import {OrderByPipe} from "@app/shared/pipes/order-by.pipe";
import {NgbModal, NgbTooltipModule} from '@ng-bootstrap/ng-bootstrap';
import {RoleSelectionModalComponent} from "@app/shared/modals/role-selection/role-selection-modal.component";


@Component({
    selector: "src-user",
    templateUrl: "./user.component.html",
    standalone: true,
    imports: [NgbTooltipModule, NgSelectComponent, FormsModule, NgOptionComponent, ReceiptComponent, TranslateModule, OrderByPipe]
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
  private readonly modalService = inject(NgbModal);

  selectedRole = {value: []};

  constructor() {
    this.onQueryParameterChangeListener();
  }

  onChangeLanguage(language: string) {
    this.translationService.setLanguage(language);
    this.appConfigService.reload();
  }
  
  canSwitchUser() {
    if (this.preferences.dataModel &&
	this.preferences.dataModel.profile &&
        Array.isArray(this.preferences.dataModel.profile.roles) &&
        this.preferences.dataModel.profile.roles.length > 1) {
      return true;
    } else {
      return false;
    }
  }

  onQueryParameterChangeListener() {
    this.activatedRoute.queryParams.subscribe(params => {
      const storedLang = sessionStorage.getItem("language");
      const langParam = params['lang'];
      const languagesEnabled = this.appDataService.public.node.languages_enabled;

      if (langParam && langParam !== storedLang && languagesEnabled.includes(langParam)) {
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

        window.location.reload();
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

  openSwitchUserModal(): void {
    const modalRef = this.modalService.open(RoleSelectionModalComponent, { backdrop: 'static', keyboard: false });
    const roles = this.preferences.dataModel.profile.roles.map((role: string) => {
      const capitalizedRole = role === 'receiver' ? 'Recipient' : role.charAt(0).toUpperCase() + role.slice(1);
      return { value: role, role: capitalizedRole };
    });
    modalRef.componentInstance.roles = roles;
    modalRef.result
      .then((selectedRole: { value: string; role: string }) => {
        this.httpService.requestRoleSwitch(selectedRole.value).subscribe({
          next: (response: { redirect: string }) => {
            if (response.redirect) {
              window.open(response.redirect);
            }
          },
        });
      }, () => { /* dismissed */ });
  }
}
