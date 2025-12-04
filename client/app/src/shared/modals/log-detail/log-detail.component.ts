import {Component, Input, OnInit, inject} from "@angular/core";
import {NgbActiveModal, NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {FormsModule} from "@angular/forms";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";
@Component({
  selector: 'src-log-detail',
  templateUrl: './log-detail.component.html',
  standalone: true,
  imports: [
    FormsModule,
    TranslateModule,
    TranslatorPipe
  ],
})
export class LogDetailComponent implements OnInit {
  protected modalService = inject(NgbModal);
  protected activeModal = inject(NgbActiveModal);

  @Input() arg: any;
  data: any;

  ngOnInit(): void {
    this.data = this.arg.data
  }

  cancel() {
    this.modalService.dismissAll();
  }
  getKeys(obj: any): string[] {
    return obj ? Object.keys(obj) : [];
  }

  formatKey(key: string): string {
    return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  }

  formatValue(value: any): string {
    if (value === null || value === undefined) return '-';
    if (typeof value === 'boolean') return value ? 'Yes' : 'No';
    if (typeof value === 'object') return JSON.stringify(value);

    if (typeof value === 'number' && value > 1000000000) {
      return new Date(value * 1000).toLocaleString();
    }

    return String(value);
  }

  isSimpleValue(value: any): boolean {
    return typeof value !== 'object' || value === null;
  }

  isOldNewObject(value: any): boolean {
    return typeof value === 'object' && value !== null &&
      ('old' in value || 'new' in value);
  }

  isRedactionField(key: string): boolean {
    return key.includes('redaction');
  }

  formatRedactionRanges(ranges: any[]): string {
    if (!ranges || ranges.length === 0) return '';
    return ranges.map(range => `[${range.start}-${range.end}]`).join(', ');
  }
}
