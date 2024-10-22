import { Component } from '@angular/core';
import {Location} from '@angular/common';
import { FileItem } from "@app/models/reciever/sendtip-data";
import { ActivatedRoute } from '@angular/router';
import { TipService } from '@app/shared/services/tip-service';
import { Forwarding, RecieverTipData } from '@app/models/reciever/reciever-tip-data';
import { HttpService } from '@app/shared/services/http.service';
import { ReceiverTipService } from '@app/services/helper/receiver-tip.service';
import { UtilsService } from '@app/shared/services/utils.service';
import { Observable } from 'rxjs';
import { PreferenceResolver } from '@app/shared/resolvers/preference.resolver';



@Component({
  selector: "src-sendtip-detail",
  templateUrl: "./sendtip-detail.component.html",
})
export class SendtipDetailComponent{

  detail: any;
  organizations: Forwarding[] = []

  files: FileItem[] = [];

  tip_id: string | null;
  tip: any;



  loading = true;


  constructor(private readonly _location: Location, private readonly tipService: TipService, protected utils: UtilsService, protected RTipService: ReceiverTipService,  private readonly httpService: HttpService, private readonly activatedRoute: ActivatedRoute, protected preferencesService: PreferenceResolver){
    this.tip = this.RTipService.tip;

    this.detail = this.RTipService.forwarding;

    if (typeof this.detail.questionnaire.answers  === 'string' || this.detail.questionnaire.answers instanceof String)
      this.detail.questionnaire.answers = JSON.parse(this.detail.questionnaire.answers)

    this.tipService.preprocessForwardingAnswers(this.detail);
  }

  backClicked() {
    this._location.back();
  }


  loadDetail() {
    
    const requestObservable: Observable<any> = this.httpService.receiverTip(this.tip_id);
    this.loading = true;
    this.RTipService.reset();
    
    requestObservable.subscribe(
      {
        next: (response: RecieverTipData) => {
          this.loading = false;
          this.RTipService.initialize(response);
          this.tip = this.RTipService.tip;
          this.activatedRoute.queryParams.subscribe((params: { [x: string]: string; }) => {
            this.tip.tip_id = params["tip_id"];
          });

        }
      }
    );

  }


  onFileUploaded(newFile: FileItem) {
    this.files.push(newFile);
  }

  onFileVerified(verifiedStatus: string) {
    console.log('File verificato:', verifiedStatus);
  }

  onFileDeleted(deletedFile: FileItem) {
    this.files = this.files.filter(file => file.id !== deletedFile.id);
  }

  listenToFields(){
    // this.loadDetail();
  }
}
