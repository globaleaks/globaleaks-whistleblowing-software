import { Pipe, PipeTransform, inject } from "@angular/core";
import {TranslateService} from "@ngx-translate/core";

@Pipe({
    name: "translate",
    pure: false,
    standalone: true,
})
export class TranslatorPipe implements PipeTransform {
  private translate = inject(TranslateService);


  transform(key: string): string {
    
    if (!key) {
      return key;
    }

    let translation = this.translate.instant(key);

    this.translate.onLangChange.subscribe(() => {
      translation = this.translate.instant(key);
    });

    return translation;
  }
}
