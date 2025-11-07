import {LanguagesSupported} from "@app/models/app/public-model";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";

export class LanguageUtils {
  public languages_supported: Record<string, LanguagesSupported> = {};
  public languagesEnabled: Record<string, LanguagesSupported> = {};
  public languages_enabled_selector: LanguagesSupported[] = [];

  constructor(private nodeResolver: NodeResolver) {
  }

  updateLanguages() {
    this.languages_supported = {};
    this.languagesEnabled = {};
    this.languages_enabled_selector = [];

    this.nodeResolver.dataModel.languages_supported.forEach((lang: LanguagesSupported) => {
      this.languages_supported[lang.code] = lang;

      if (this.nodeResolver.dataModel.languages_enabled.indexOf(lang.code) !== -1) {
        this.languagesEnabled[lang.code] = lang;
        this.languages_enabled_selector.push(lang);
      }
    });
  }
}