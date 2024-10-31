import {Component, ElementRef, Input, OnInit, ViewChild, inject} from "@angular/core";
import {NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {DomSanitizer, SafeResourceUrl} from "@angular/platform-browser";
import {UtilsService} from "@app/shared/services/utils.service";
import {WbFile} from "@app/models/app/shared-public-model";
import {AuthenticationService} from "@app/services/helper/authentication.service";

import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";

@Component({
    selector: "src-file-view",
    templateUrl: "./file-view.component.html",
    standalone: true,
    imports: [TranslateModule, TranslatorPipe]
})
export class FileViewComponent implements OnInit {
  private authenticationService = inject(AuthenticationService);
  private sanitizer = inject(DomSanitizer);
  private utilsService = inject(UtilsService);
  private modalService = inject(NgbModal);

  @Input() args: {
    file: WbFile,
    loaded: boolean,
    iframeHeight: number
  };
  @ViewChild("viewer") viewerFrame: ElementRef;

  iframeUrl: SafeResourceUrl;

  ngOnInit() {
    this.iframeUrl = this.sanitizer.bypassSecurityTrustResourceUrl("viewer/index.html");
    this.args.iframeHeight = window.innerHeight * 0.75;
    this.viewFile();
  }

  viewFile() {
    const url = this.authenticationService.session.role === "whistleblower"?"api/whistleblower/wbtip/wbfiles/":"api/recipient/wbfiles/";
    this.utilsService.view(this.authenticationService, url + this.args.file.id, this.args.file.type, (blob: Blob) => {
      this.args.loaded = true;
      window.addEventListener("message", () => {
        const data = {
          tag: this.getFileTag(this.args.file.type),
          blob: blob
        };
        const iframeElement = this.viewerFrame.nativeElement;
        iframeElement.contentWindow.postMessage(data, "*");

      }, {once: true});
    });
  }

  getFileTag(type: string) {
    if (type === "application/pdf") {
      return "pdf";
    } else if (type.indexOf("audio/") === 0) {
      return "audio";
    } else if (type.indexOf("image/") === 0) {
      return "image";
    } else if (type === "text/csv" || type === "text/plain") {
      return "txt";
    } else if (type.indexOf("video/") === 0) {
      return "video";
    } else {
      return "none";
    }
  };

  cancel() {
    this.modalService.dismissAll();
  }
}
