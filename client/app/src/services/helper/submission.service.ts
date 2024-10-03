import {Injectable} from "@angular/core";
import {AppDataService} from "@app/app-data.service";
import {HttpService} from "@app/shared/services/http.service";
import {Context} from "@app/models/reciever/reciever-tip-data";
import {submissionResourceModel} from "@app/models/whistleblower/submission-resource";

@Injectable({
  providedIn: "root",
})
export class SubmissionService {
  submission: submissionResourceModel = new submissionResourceModel();
  context: Context;
  receivers: string[] = [];
  mandatory_receivers = 0;
  optional_receivers = 0;
  selected_receivers: { [key: string]: boolean } = {};
  override_receivers: string[] = [];
  blocked = false;
  uploads: { [key: string]: any };
  private sharedData: Flow[] = [];

  constructor(private httpService: HttpService, private appDataService: AppDataService) {
  }

  setContextReceivers(context_id: number) {
    this.context = this.appDataService.contexts_by_id[context_id];

    if (Object.keys(this.selected_receivers).length && this.context.allow_recipients_selection) {
      return;
    }

    this.selected_receivers = {};
    this.receivers = [];

    this.context.receivers.forEach((receiver: string) => {
      const r = this.appDataService.receivers_by_id[receiver];

      if (!r) {
        return;
      }

      this.receivers.push(r);

      if (r.forcefully_selected) {
        this.mandatory_receivers += 1;
      } else {
        this.optional_receivers += 1;
      }

      if (this.context.select_all_receivers || r.forcefully_selected) {
        this.selected_receivers[r.id] = true;
      }
    });
  }

  countSelectedReceivers() {
    return Object.keys(this.selected_receivers).length;
  }

  create(context_id: number) {
    this.setContextReceivers(context_id);
    this.submission.context_id = context_id;
  }

  submit() {
    this.submission.receivers = [];

    if (this.override_receivers.length) {
      this.submission.receivers = this.override_receivers;
    } else {
      for (const key in this.selected_receivers) {
        if (Object.prototype.hasOwnProperty.call(this.selected_receivers, key)) {
          this.submission.receivers.push(key);
        }
      }
    }

    if (!this.submission.identity_provided) {
      this.submission.identity_provided = false;
    }

    const _submission_data = {
      context_id: this.submission.context_id,
      receivers: this.submission.receivers,
      identity_provided: this.submission.identity_provided,
      answers: this.submission.answers,
      answer: this.submission.answer,
      score: this.submission.score,
    };

    const param = JSON.stringify(_submission_data);
    return this.httpService.requestReportSubmission(param);
  }

  setSharedData(data:Flow| null) {
    if(data){
      this.sharedData.push(data);
    }
  }

  getSharedData() {
    return this.sharedData;
  }
}
