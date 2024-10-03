import {Component, Input, OnInit} from "@angular/core";
import {NgForm} from "@angular/forms";
import {LanguageUtils} from "@app/pages/admin/settings/helper-methods/language-utils";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import {AppConfigService} from "@app/services/root/app-config.service";
import {TranslationService} from "@app/services/helper/translation.service";
import {AppDataService} from "@app/app-data.service";
import {LanguagesSupported} from "@app/models/app/public-model";

@Component({
  selector: "src-tab3",
  templateUrl: "./tab3.component.html"
})
export class Tab3Component implements OnInit {
  @Input() contentForm: NgForm;

  showLangSelect = false;
  selected = {value: []};
  languageUtils: LanguageUtils

  constructor(private appDataService: AppDataService, private translationService: TranslationService, private appConfigService: AppConfigService, private utilsService: UtilsService, protected nodeResolver: NodeResolver) {
  }

  ngOnInit(): void {
    this.updateLanguages();
  }

  updateLanguages(): void {
    this.languageUtils = new LanguageUtils(this.nodeResolver);
    this.languageUtils.updateLanguages();
  }

  toggleLangSelect() {
    this.showLangSelect = !this.showLangSelect;
  }

  langNotEnabledFilter(language: LanguagesSupported) {
    return this.nodeResolver.dataModel.languages_enabled.indexOf(language.code) === -1;
  }

  enableLanguage(language: LanguagesSupported) {
    if (language && (this.nodeResolver.dataModel.languages_enabled.indexOf(language.code) === -1)) {
      this.nodeResolver.dataModel.languages_enabled.push(language.code);
    }
    this.selected.value = []
  }

  removeLang(index: number, lang_code: string) {
    if (lang_code === this.nodeResolver.dataModel.default_language) {
      return;
    }
    this.nodeResolver.dataModel.languages_enabled.splice(index, 1);
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