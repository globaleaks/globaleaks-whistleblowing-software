import {Component, OnInit, inject, input} from "@angular/core";
import {NgForm, FormsModule} from "@angular/forms";
import {LanguageUtils} from "@app/pages/admin/settings/helper-methods/language-utils";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import {AppConfigService} from "@app/services/root/app-config.service";
import {AppDataService} from "@app/app-data.service";
import {SelectionEditorComponent, SelectionEntry} from "@app/shared/components/selection-editor/selection-editor.component";
import {LanguagesSupported} from "@app/models/app/public-model";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-tab3",
    templateUrl: "./tab3.component.html",
    standalone: true,
    imports: [FormsModule, SelectionEditorComponent, TranslateModule]
})
export class Tab3Component implements OnInit {
  private appConfigService = inject(AppConfigService);
  private appDataService = inject(AppDataService);
  private utilsService = inject(UtilsService);
  protected nodeResolver = inject(NodeResolver);

  readonly contentForm = input.required<NgForm>();

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

  getNotEnabledLanguages() {
    return this.nodeResolver.dataModel.languages_supported.filter(lang => !this.nodeResolver.dataModel.languages_enabled.includes(lang.code));
  }

  get languageOptions(): SelectionEntry[] {
    return this.languagesNotEnabled.map(lang => ({id: lang.code, label: lang.name + " [" + lang.code + "]"}));
  }

  get enabledLanguages(): SelectionEntry[] {
    return this.nodeResolver.dataModel.languages_enabled.map(code => ({id: code, label: this.languageUtils.languages_supported[code].name + " [" + code + "]"}));
  }

  enableLanguage(lang_code: string) {
    if (lang_code && (this.nodeResolver.dataModel.languages_enabled.indexOf(lang_code) === -1)) {
      this.nodeResolver.dataModel.languages_enabled.push(lang_code)
      this.nodeResolver.dataModel.languages_enabled.sort();
      this.languagesNotEnabled = this.getNotEnabledLanguages();
    }
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
      this.appConfigService.reinit();
      this.utilsService.reloadCurrentRoute();
    });
  }
}
