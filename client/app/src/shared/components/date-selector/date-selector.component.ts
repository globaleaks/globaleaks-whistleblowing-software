import {Component, EventEmitter, Input, Output} from "@angular/core";
import {NgbDate, NgbDatepickerModule} from "@ng-bootstrap/ng-bootstrap";
import {FormsModule} from "@angular/forms";

@Component({
  selector: "ngbd-datepicker-range",
  standalone: true,
  imports: [NgbDatepickerModule, FormsModule],
  templateUrl: "./date-selector.component.html"
})
export class DateRangeSelectorComponent {
  hoveredDate: NgbDate | null = null;
  @Output() emitDateSelection = new EventEmitter<{ fromDate: string | null; toDate: string | null }>();
  @Input() currentDates: { fromDate: NgbDate | null, toDate: NgbDate | null } | null;
  fromDate: NgbDate | null = null;
  toDate: NgbDate | null = null;

  onDateSelection(date: NgbDate) {
    if (!this.fromDate && !this.toDate) {
      this.fromDate = date;
    } else if (this.fromDate && !this.toDate && date.after(this.fromDate)) {
      this.toDate = date;
    } else {
      this.toDate = null;
      this.fromDate = date;
    }
    if (this.fromDate && this.toDate) {
      const formattedFromDate = this.formatDate(this.fromDate);
      const formattedToDate = this.formatDate(this.toDate);
      this.emitDateSelection.emit({fromDate: formattedFromDate, toDate: formattedToDate});
    }
  }

  isHovered(date: NgbDate) {
    return (
      this.fromDate &&
      !this.toDate &&
      this.hoveredDate &&
      date.after(this.fromDate) &&
      date.before(this.hoveredDate)
    );
  }

  isInside(date: NgbDate) {
    return this.toDate && date.after(this.fromDate) && date.before(this.toDate);
  }

  resetDatepicker() {
    this.fromDate = null;
    this.toDate = null;
    this.emitDateSelection.emit({fromDate: null, toDate: null});
  }

  isRange(date: NgbDate) {
    return (
      date.equals(this.fromDate) ||
      (this.toDate && date.equals(this.toDate)) ||
      this.isInside(date) ||
      this.isHovered(date)
    );
  }

  formatDate(date: NgbDate): string {
    const jsDate = new Date(date.year, date.month - 1, date.day);
    return jsDate.toString();
  }
}
