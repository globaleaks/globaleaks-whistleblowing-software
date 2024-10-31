import {Component, Input, OnInit, inject} from "@angular/core";
import {NgForm, FormsModule} from "@angular/forms";
import {LanguageUtils} from "@app/pages/admin/settings/helper-methods/language-utils";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import {AppConfigService} from "@app/services/root/app-config.service";
import {TranslationService} from "@app/services/helper/translation.service";
import {AppDataService} from "@app/app-data.service";
import {LanguagesSupported} from "@app/models/app/public-model";
import {NgSelectComponent, NgOptionTemplateDirective} from "@ng-select/ng-select";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {FilterPipe} from "@app/shared/pipes/filter.pipe";
import {TranslateModule} from "@ngx-translate/core";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";

@Component({
    selector: "src-tab3",
    templateUrl: "./tab3.component.html",
    standalone: true,
    imports: [FormsModule, NgSelectComponent, NgOptionTemplateDirective, NgbTooltipModule, TranslatorPipe, FilterPipe, TranslateModule]
})
export class Tab3Component implements OnInit {
  private appDataService = inject(AppDataService);
  private translationService = inject(TranslationService);
  private appConfigService = inject(AppConfigService);
  private utilsService = inject(UtilsService);
  protected nodeResolver = inject(NodeResolver);

  @Input() contentForm: NgForm;

  showLangSelect = false;
  selected = {value: []};
  languageUtils: LanguageUtils
  languagesNotEnabled: LanguagesSupported[];

  ngOnInit(): void {
    this.updateLanguages();
  }

  updateLanguages(): void {
    this.languageUtils = new LanguageUtils(this.nodeResolver);
    this.languageUtils.updateLanguages();
    this.languagesNotEnabled = this.getNotEnabledLanguages();
  }

  toggleLangSelect() {
    this.showLangSelect = !this.showLangSelect;
  }

  getNotEnabledLanguages() {
    return this.nodeResolver.dataModel.languages_supported.filter(lang => !this.nodeResolver.dataModel.languages_enabled.includes(lang.code));
  }

  enableLanguage(language: LanguagesSupported) {
    if (language && (this.nodeResolver.dataModel.languages_enabled.indexOf(language.code) === -1)) {
      this.nodeResolver.dataModel.languages_enabled.push(language.code)
      this.nodeResolver.dataModel.languages_enabled.sort();
      this.languagesNotEnabled = this.getNotEnabledLanguages();
    }
    this.selected.value = [];
  }

  removeLang(index: number, lang_code: string) {
    if (lang_code === this.nodeResolver.dataModel.default_language) {
      return;
    }
    this.nodeResolver.dataModel.languages_enabled.splice(index, 1);
    this.languagesNotEnabled = this.getNotEnabledLanguages();
  }

  updateNode() {
    this.utilsService.update(this.nodeResolver.dataModel).subscribe(res => {
      this.appDataService.public.node.languages_enabled = res["languages_enabled"];
      sessionStorage.removeItem("default_language");
      const reloadComponent = () => {
        this.utilsService.reloadCurrentRoute();
      };
      this.translationService.onChange(res["default_language"], reloadComponent);
      this.appConfigService.reinit(false);
    });
  }
}
