import { Component, OnInit } from '@angular/core';
import {Location} from '@angular/common';
import { FileItem, SentTipDetail } from "@app/models/reciever/sendtip-data";
import { ActivatedRoute, Router } from '@angular/router';
import { TipService } from '@app/shared/services/tip-service';
import { Forwarding, RecieverTipData } from '@app/models/reciever/reciever-tip-data';
import { Observable } from 'rxjs';
import { HttpService } from '@app/shared/services/http.service';
import { ReceiverTipService } from '@app/services/helper/receiver-tip.service';
import { TranslateService } from '@ngx-translate/core';
import { UtilsService } from '@app/shared/services/utils.service';

@Component({
  selector: "src-sendtip-detail",
  templateUrl: "./sendtip-detail.component.html",
})
export class SendtipDetailComponent implements OnInit {

  detail: Forwarding;
  organizations: Forwarding[] = []

  files: FileItem[] = [];

  tip_id: string | null;
  tip: RecieverTipData;

  loading = true;

  redactOperationTitle: string;

  constructor(private _location: Location, private tipService: TipService, protected utils: UtilsService, private translateService: TranslateService, protected RTipService: ReceiverTipService,  private httpService: HttpService, private activatedRoute: ActivatedRoute){}

  backClicked() {
    this._location.back();
  }

  ngOnInit(): void {
    this.loadDetail();
  }

  loadDetail() {
    this.tip_id = this.activatedRoute.snapshot.paramMap.get("tip_id");

    this.detail = this.RTipService.forwarding;
    this.organizations.push(this.detail);

    this.redactOperationTitle = this.translateService.instant('Mask') + ' / ' + this.translateService.instant('Redact');
    
    const requestObservable: Observable<any> = this.httpService.receiverTip(this.tip_id);
    this.loading = true;
    this.RTipService.reset();
    
    requestObservable.subscribe(
      {
        next: (response: RecieverTipData) => {
          
          this.RTipService.initialize(response);
          this.tip = this.RTipService.tip;

          this.activatedRoute.queryParams.subscribe((params: { [x: string]: string; }) => {
            this.tip.tip_id = params["tip_id"];
          });

          this.tip.receivers_by_id = this.utils.array_to_map(this.tip.receivers);

          this.tipService.preprocessTipAnswers(this.tip, true);
          
          this.loading = false;
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
}
