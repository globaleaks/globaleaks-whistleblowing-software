import { Component, OnInit, inject } from "@angular/core";
import {NgbActiveModal, NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {AppDataService} from "@app/app-data.service";
import {Node} from "@app/models/app/public-model";
import { MarkdownComponent } from "ngx-markdown";
import { TranslateModule } from "@ngx-translate/core";
import { TranslatorPipe } from "@app/shared/pipes/translate";
import { StripHtmlPipe } from "@app/shared/pipes/strip-html.pipe";

@Component({
    selector: "src-disclaimer",
    templateUrl: "./disclaimer.component.html",
    standalone: true,
    imports: [
        MarkdownComponent,
        TranslateModule,
        TranslatorPipe,
        StripHtmlPipe,
    ],
})
export class DisclaimerComponent implements OnInit {
  private activeModal = inject(NgbActiveModal);
  private modalService = inject(NgbModal);
  protected appDataService = inject(AppDataService);

  nodeData: Node;

  confirmFunction: () => void;

  ngOnInit(): void {
    if (this.appDataService.public.node) {
      this.nodeData = this.appDataService.public.node;
    }
  }

  confirm() {
    this.confirmFunction();
    return this.activeModal.close();
  }

  cancel() {
    this.modalService.dismissAll();
  }
}
