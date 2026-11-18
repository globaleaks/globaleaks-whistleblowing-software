import {Injectable, inject} from "@angular/core";
import {AppDataService} from "@app/app-data.service";
import {HttpService} from "@app/shared/services/http.service";
import {Context} from "@app/models/receiver/receiver-tip-data";
import {submissionResourceModel} from "@app/models/whistleblower/submission-resource";

@Injectable({
  providedIn: "root",
})
export class SubmissionService {
  private readonly httpService = inject(HttpService);
  private readonly appDataService = inject(AppDataService);

  submission: submissionResourceModel = new submissionResourceModel();
  context: Context;
  receivers: string[] = [];
  mandatory_receivers = 0;
  optional_receivers = 0;
  selected_receivers: Record<string, boolean> = {};
  override_receivers: string[] = [];
  blocked = false;
  uploads: Record<string, any>;
  private readonly sharedData: Flow[] = [];

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

  getSelectedReceivers(): string[] {
    return this.override_receivers.length ? this.override_receivers : Object.keys(this.selected_receivers);
  }

  getEffectiveReceivers(): string[] {
    const receivers = this.getSelectedReceivers();
    const supplementary = receivers.length === 0 ? this.context.supplementary_receivers_if_none :
      (receivers.length === 1 ? this.context.supplementary_receivers_if_single : []);
    return [...new Set([...receivers, ...(supplementary || [])])];
  }

  submit() {
    this.submission.receivers = this.getSelectedReceivers();

    if (!this.submission.identity_provided) {
      this.submission.identity_provided = false;
    }

    const _submission_data = {
      context_id: this.submission.context_id,
      receivers: this.submission.receivers,
      identity_provided: this.submission.identity_provided,
      answers: this.submission.answers,
      answer: this.submission.answer,
      receipt: this.submission.receipt
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
