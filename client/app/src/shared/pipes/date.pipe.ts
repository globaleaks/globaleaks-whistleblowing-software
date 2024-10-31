import {Pipe, PipeTransform} from "@angular/core";

const LOCALE = navigator.languages
  ? navigator.languages[0]
  : (navigator.language || (navigator as { userLanguage?: string }).userLanguage);

type Formats = "short" | "medium" | "shortDate";

const predefinedFormats: Record<Formats, Intl.DateTimeFormatOptions> = {
  short: {
    timeStyle: "short",
    dateStyle: "short"
  },
  medium: {
    timeStyle: "medium",
    dateStyle: "medium"
  },
  shortDate: {
    dateStyle: "short",
  }
};

@Pipe({
    name: "datse",
    standalone: true,
})

export class DatePipe implements PipeTransform {

  transform(value: Parameters<Intl.DateTimeFormat["format"]>[0], format: Formats = "short") {
    return new Intl.DateTimeFormat(LOCALE, predefinedFormats[format]).format(value);
  }
}
