import {Pipe, PipeTransform} from "@angular/core";
import * as DOMPurify from 'dompurify';

@Pipe({
    name: "stripHtml",
    standalone: true
})
export class StripHtmlPipe implements PipeTransform {

  transform(value: string): string {
    // Use DOMPurify to sanitize input
    return (DOMPurify as any).default.sanitize(value);
  }
}
