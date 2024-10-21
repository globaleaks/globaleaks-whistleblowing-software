import {HttpClient} from "@angular/common/http";
import {Component, ElementRef, forwardRef, Input, OnInit, ViewChild, inject} from "@angular/core";
import {DomSanitizer, SafeResourceUrl} from "@angular/platform-browser";
import {AppDataService} from "@app/app-data.service";
import {WbFile} from "@app/models/app/shared-public-model";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {ReceiverTipService} from "@app/services/helper/receiver-tip.service";
import {WbtipService} from "@app/services/helper/wbtip.service";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {HttpService} from "@app/shared/services/http.service";
import {MaskService} from "@app/shared/services/mask.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {DatePipe} from "@angular/common";
import {TipFieldComponent} from "../tip-field/tip-field.component";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {SplitPipe} from "@app/shared/pipes/split.pipe";
import {OrderByPipe} from "@app/shared/pipes/order-by.pipe";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";

@Component({
    selector: "src-tip-field-answer-entry",
    templateUrl: "./tip-field-answer-entry.component.html",
    standalone: true,
    imports: [forwardRef(() => TipFieldComponent), DatePipe, TranslateModule, TranslatorPipe, SplitPipe, OrderByPipe, NgbTooltipModule]
})
export class TipFieldAnswerEntryComponent implements OnInit {
  protected httpService = inject(HttpService);
  protected appDataService = inject(AppDataService);
  protected modalService = inject(NgbModal);
  protected utilsService = inject(UtilsService);
  private maskService = inject(MaskService);
  protected preferenceResolver = inject(PreferenceResolver);
  private http = inject(HttpClient);
  private sanitizer = inject(DomSanitizer);
  protected authenticationService = inject(AuthenticationService);
  private wbTipService = inject(WbtipService);
  private rTipService = inject(ReceiverTipService);

  @Input() entry: any;
  @Input() field: any;
  @Input() fieldAnswers: any;
  @Input() redactOperationTitle: string;
  @Input() redactMode: boolean;

  format = "dd/MM/yyyy";
  locale = "en-US";
  audioFiles: { [reference_id: string]: Blob } = {};
  iframeUrl: SafeResourceUrl;
  @ViewChild("viewer") viewerFrame: ElementRef;
  tipService:WbtipService|ReceiverTipService;
  filteredWbFiles: WbFile[];
  wbfile:WbFile;

  ngOnInit(): void {
    if (this.authenticationService.session.role === "whistleblower") {
      this.tipService = this.wbTipService;
    }
    if(this.authenticationService.session.role === "receiver") {
      this.tipService = this.rTipService;
    }
    if(this.tipService.tip){
      this.filteredWbFiles = this.filterWbFilesByReferenceId(this.tipService.tip.wbfiles);
    }
    if(this.field.type === "voice"){
      this.iframeUrl = this.sanitizer.bypassSecurityTrustResourceUrl("viewer/index.html");
      this.loadAudioFile(this.field.id);
    }
  }

  loadAudioFile(reference_id: string): void {
     for (const wbfile of this.tipService.tip.wbfiles) {
        if (wbfile.reference_id === reference_id) {
        const id = wbfile.id;
        const url = this.getApiUrl(id);

        this.http.get(url, {
          headers: {
            'x-session': this.authenticationService.session.id
          },
          responseType: 'blob'
        }).subscribe((response: Blob) => {
          this.audioFiles[reference_id] = response;
          window.addEventListener("message", (message: MessageEvent) => {
            const iframe = this.viewerFrame?.nativeElement;
            if (message.source !== iframe?.contentWindow) {
              return;
            }
            const data = {
              tag: "audio",
              blob: this.audioFiles[reference_id],
            };
            iframe.contentWindow.postMessage(data, "*");
          });
        });

        break;
       }
      }
  }

  private getApiUrl(id: string): string {
    const role = this.authenticationService.session.role;
    return role === 'whistleblower' ?
      `api/whistleblower/wbtip/wbfiles/${id}` :
      `api/recipient/wbfiles/${id}`;
  }

  redactInformation(type:string, field:any, entry:string, content:string){
    if (this.checkIdExists(this.tipService.tip.data,field.id)){
      this.maskService.redactInfo("whistleblower_identity",field.id,entry,content,this.tipService.tip);
    } else {
      this.maskService.redactInfo(type,field.id,entry,content,this.tipService.tip);
    }
  }

  checkIdExists(data: any, id: string): boolean {
    if (!data || typeof data !== 'object') {
        return false;
    }

    if (data[id]) {
        return true;
    }

    for (const key in data) {
        if (typeof data[key] === 'object') {
            if (this.checkIdExists(data[key], id)) {
                return true;
            }
        }
    }

    return false;
  }

  maskContent(id: string, index: string, value: string) {
   return this.maskService.maskingContent(id,index,value,this.tipService.tip)
  }

  filterWbFilesByReferenceId(wbfiles: WbFile[]): WbFile[] {
    return wbfiles.filter((wbfile: WbFile) => wbfile.reference_id === this.field.id);
  }
  
  selectedFile(file: WbFile) {
    this.wbfile = file;
  }
}
