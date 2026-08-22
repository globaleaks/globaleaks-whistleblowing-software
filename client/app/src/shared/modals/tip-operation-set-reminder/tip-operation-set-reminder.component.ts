import {Component, OnInit, inject} from "@angular/core";
import {NgbDateStruct, NgbModal, NgbInputDatepicker} from "@ng-bootstrap/ng-bootstrap";
import {UtilsService} from "@app/shared/services/utils.service";
import {HttpService} from "@app/shared/services/http.service";
import {FormsModule} from "@angular/forms";
import {TranslateModule} from "@ngx-translate/core";


@Component({
    selector: "src-tip-operation-set-reminder",
    templateUrl: "./tip-operation-set-reminder.component.html",
    standalone: true,
    imports: [NgbInputDatepicker, FormsModule, TranslateModule]
})
export class TipOperationSetReminderComponent implements OnInit {
  private modalService = inject(NgbModal);
  private httpService = inject(HttpService);
  private utils = inject(UtilsService);

  args: any;

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

      return this.httpService.tipOperation(req.operation, req.args, this.args.tip.id)
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
    this.httpService.tipOperation(req.operation, req.args, this.args.tip.id)
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
