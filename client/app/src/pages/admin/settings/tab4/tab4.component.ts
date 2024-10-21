import { Component, Input, OnInit, inject } from "@angular/core";
import { NgForm, FormsModule } from "@angular/forms";
import {LanguageUtils} from "@app/pages/admin/settings/helper-methods/language-utils";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import { NgClass } from "@angular/common";
import { TranslatorPipe } from "@app/shared/pipes/translate";
import { TranslateModule } from "@ngx-translate/core";

@Component({
    selector: "src-tab4",
    templateUrl: "./tab4.component.html",
    standalone: true,
    imports: [FormsModule, NgClass, TranslatorPipe, TranslateModule]
})
export class Tab4Component implements OnInit {
  protected utilsService = inject(UtilsService);
  protected nodeResolver = inject(NodeResolver);

  @Input() contentForm: NgForm;

  vars: { language_to_customize: string, text_to_customize: string, custom_text: string } = {
    language_to_customize: "",
    text_to_customize: "",
    custom_text: ""
  };
  custom_texts: { [key: string]: string } = {}
  default_texts: { [key: string]: string } = {}
  custom_texts_selector: { key: string; value: string; }[] = [];
  customTextsExist: boolean = false;
  languageUtils: LanguageUtils

  ngOnInit(): void {
    this.initLanguages();
  }

  initLanguages(): void {
    this.languageUtils = new LanguageUtils(this.nodeResolver);
    this.languageUtils.updateLanguages();

    this.vars.language_to_customize = this.nodeResolver.dataModel.default_language
    this.getl10n(this.vars.language_to_customize);
  }


  getl10n(lang: string): void {
    if (!lang) {
      return;
    }
    this.utilsService.AdminL10NResource(lang).subscribe(res => {
      this.custom_texts = res;
      this.customTextsExist = Object.keys(this.custom_texts).length > 0;
    });

    this.customTextsKeys();
    this.utilsService.DefaultL10NResource(lang).subscribe(default_texts => {
      const list = [];
      for (const key in default_texts) {
        if (Object.prototype.hasOwnProperty.call(default_texts, key)) {
          let value = default_texts[key];
          if (value.length > 150) {
            value = value.slice(0, 150) + "...";
          }
          list.push({"key": key, "value": value});
        }
      }
      this.default_texts = default_texts;
      this.custom_texts_selector = list.sort((a, b) => a.value.localeCompare(b.value));
    });
  }

  customTextsKeys(): { key: string }[] {
    return Object.keys(this.custom_texts).map(key => ({key}));
  }

  updateCustomText(data: { [key: string]: string }, lang: string) {
    this.utilsService.updateAdminL10NResource(data, lang).subscribe(_ => {
      this.utilsService.reloadComponent();
    });
  }

  deleteCustomText(dict: { [key: string]: string; }, key: string): void {
    delete dict[key];
  }

}