import {Injectable} from "@angular/core";
import {HttpService} from "@app/shared/services/http.service";
import {AppDataService} from "@app/app-data.service";
import {Forwarding, RecieverTipData} from "@app/models/reciever/reciever-tip-data";
import {UtilsService} from "@app/shared/services/utils.service";
import { RedactionData } from "@app/models/component-model/redaction";

@Injectable({
  providedIn: "root"
})
export class ReceiverTipService {
  tip: RecieverTipData = new RecieverTipData();

  forwarding: Forwarding;

  constructor(private httpService: HttpService, private appDataService: AppDataService,protected utils: UtilsService) {
  }

  reset() {
    this.tip = new RecieverTipData();
  }

  initialize(response: RecieverTipData) {
    this.tip = response;
    this.tip.context = this.appDataService.contexts_by_id[this.tip.context_id];
    this.tip.questionnaire = this.appDataService.questionnaires_by_id[this.tip.context["questionnaire_id"]];
    this.tip.msg_receiver_selected = null;
    this.tip.msg_receivers_selector = this.getMsgReceiversSelector();
  }


  operation(url: string, operation: string, args: { key: string, value: boolean }) {
    return this.httpService.runOperation(url, operation, args, false).subscribe({});
  }

  newComment(content: string, visibility: string, organizations?: number[]) {
    const param = JSON.stringify({"id": this.tip.msg_receiver_selected, "content": content, "visibility": visibility, "tids": organizations});
    return this.httpService.rTipsRequestNewComment(param, this.tip.id);
  }

  newRedaction(content:RedactionData) {
    this.httpService.requestCreateRedaction(content).subscribe(
      () => {
        this.utils.reloadComponent();
      },
    );
  }

  updateRedaction(content: RedactionData) {
    this.httpService.requestUpdateRedaction(content).subscribe(
      () => {
        this.utils.reloadComponent();
      },
    );
  }

  private getMsgReceiversSelector() {
    const msgReceiversSelector = [];

    for (const receiver of this.tip.receivers) {
      if (this.appDataService.receivers_by_id[receiver.id]) {
        const r = this.appDataService.receivers_by_id[receiver.id];
        msgReceiversSelector.push({
          key: r.id,
          value: r.name
        });
      }
    }

    return msgReceiversSelector;
  }
}
