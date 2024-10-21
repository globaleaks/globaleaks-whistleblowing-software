import {HttpClient} from "@angular/common/http";
import { Component, Input, OnInit, inject } from "@angular/core";
import { NgbDateStruct, NgbModal, NgbInputDatepicker } from "@ng-bootstrap/ng-bootstrap";
import {UtilsService} from "@app/shared/services/utils.service";
import { FormsModule } from "@angular/forms";
import { TranslateModule } from "@ngx-translate/core";
import { TranslatorPipe } from "@app/shared/pipes/translate";


@Component({
    selector: "src-tip-operation-set-reminder",
    templateUrl: "./tip-operation-set-reminder.component.html",
    standalone: true,
    imports: [NgbInputDatepicker, FormsModule, TranslateModule, TranslatorPipe]
})
export class TipOperationSetReminderComponent implements OnInit {
  private modalService = inject(NgbModal);
  private http = inject(HttpClient);
  private utils = inject(UtilsService);

  @Input() args: any;

  request_motivation: string;
  model: NgbDateStruct;

  ngOnInit() {
    const reminderDate = this.args.reminder_date;
    this.args.reminder_date = {
      year: reminderDate.getUTCFullYear(),
      month: reminderDate.getUTCMonth() + 1,
      day: reminderDate.getUTCDate()
    };
  }

  confirm() {
    this.cancel();

    if (this.args.operation === "postpone" || this.args.operation === "set_reminder") {
      let date: number;
      const {year, month, day} = this.args.reminder_date;
      const dateData = new Date(year, month - 1, day);
      const timestamp = dateData.getTime();
      if (this.args.operation === "postpone")
        date = this.args.expiration_date.getTime();
      else {
        date = timestamp;
      }

      const req = {
        "operation": this.args.operation,
        "args": {
          "value": date
        }
      };

      return this.http.put("api/recipient/rtips/" + this.args.tip.id, req)
        .subscribe(() => {
          this.reload();
        });
    }
    return;
  }

  disableReminder() {
    this.cancel();
    const req = {
      "operation": "set_reminder",
      "args": {
        "value": 32503680000000
      }
    };
    this.http.put("api/recipient/rtips/" + this.args.tip.id, req)
      .subscribe(() => {
        this.reload();
      });
  }

  reload() {
    this.utils.reloadCurrentRoute();
  }

  cancel() {
    this.modalService.dismissAll();
  }
}
