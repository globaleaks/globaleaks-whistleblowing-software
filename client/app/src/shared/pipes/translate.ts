import {Pipe, PipeTransform, inject} from "@angular/core";
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

    // The pipe is impure: it is re-evaluated on every rendering pass, so a
    // language change is picked up by the next pass without subscribing.
    return this.translate.instant(key);
  }
}
