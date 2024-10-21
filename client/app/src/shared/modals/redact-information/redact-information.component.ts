import { Component, ElementRef, Input, OnInit, ViewChild, inject } from '@angular/core';
import {ReceiverTipService} from '@app/services/helper/receiver-tip.service';
import {PreferenceResolver} from '@app/shared/resolvers/preference.resolver';
import {MaskService} from '@app/shared/services/mask.service';
import {NgbModal} from '@ng-bootstrap/ng-bootstrap';
import {RedactionData} from "@app/models/component-model/redaction";

import { FormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';
import { TranslatorPipe } from '@app/shared/pipes/translate';

@Component({
    selector: 'src-redact-information',
    templateUrl: './redact-information.component.html',
    standalone: true,
    imports: [
    FormsModule,
    TranslateModule,
    TranslatorPipe
],
})
export class RedactInformationComponent implements OnInit{
  private maskService = inject(MaskService);
  protected preferenceResolver = inject(PreferenceResolver);
  private modalService = inject(NgbModal);
  private receiverTipService = inject(ReceiverTipService);

  @ViewChild('redact', { static: false }) redactTextArea: ElementRef;
  @Input() arg:any;
  redaction: any = null;
  forced_visible: boolean = false;
  vars = {
    redaction_switch: true,
  };
  ranges_selected: any
  temporary_redaction: any[] = [];
  permanent_redaction: any[] = [];
  unmaskedContent: string = "";
  content: string = "";
  originalContent: string = "";

  cancel() {
    this.modalService.dismissAll();
  }

  ngOnInit(): void {
    this.initializeMasking();
  }

  initializeMasking() {
    this.redaction = this.arg.redaction;
    this.temporary_redaction = [];
    this.permanent_redaction = [];
    this.ranges_selected = [];

    if (this.redaction) {
      this.permanent_redaction = this.redaction.permanent_redaction;
      this.temporary_redaction = this.redaction.temporary_redaction;

      if (this.vars.redaction_switch) {
        this.ranges_selected = this.temporary_redaction;
      }
    }

    this.unmaskedContent = this.content = this.arg.data.content;
    this.originalContent = this.content = this.maskService.maskContent(this.content, this.temporary_redaction, true, String.fromCharCode(0x2591),"");
  }

  toggleMasking() {
    this.initializeMasking();
  }

  ignoreEdit(event: any) {
    if (event.keyCode >= 37 && event.keyCode <= 40) {
      return;
    }
    event.preventDefault();
  }

  toggleVisibility() {
    this.forced_visible = !this.forced_visible;
  }

  selectContent() {
    const response:any = this.maskService.getSelectedRanges(true, this.ranges_selected,this.redactTextArea);

    if (!this.vars.redaction_switch) {
      this.ranges_selected = this.maskService.intersectRanges(this.temporary_redaction, response.new_ranges);
      this.content = this.maskService.maskContent(this.content, this.ranges_selected, true, String.fromCharCode(0x2588),"");
    } else {
      if (!this.preferenceResolver.dataModel.can_mask_information) {
        this.ranges_selected = this.maskService.intersectRanges(this.temporary_redaction, response.new_ranges);
      } else {
        this.ranges_selected = response.new_ranges;
      }

      this.content = this.maskService.maskContent(this.content, this.ranges_selected, true, String.fromCharCode(0x2591),"");
      this.content = this.maskService.maskContent(this.content, this.permanent_redaction, true, String.fromCharCode(0x2588),"");
    }
  }

  unSelectContent() {
    const response:any = this.maskService.getSelectedRanges(false, this.ranges_selected,this.redactTextArea);
    this.ranges_selected = response.new_ranges;
    this.content = this.maskService.onUnHighlight(this.content, this.unmaskedContent, [response.selected_ranges]);
  }

  saveMasking() {
    const redactionData:RedactionData= {
      internaltip_id: this.arg.tip.id,
      reference_id: this.arg.data.id,
      entry: this.arg.data.entry,
      temporary_redaction: [],
      permanent_redaction: [],
    };

    if (this.vars.redaction_switch) {
      redactionData.operation = 'mask';
      redactionData.content_type = this.arg.data.type;
      redactionData.temporary_redaction = this.ranges_selected;
    } else {
      redactionData.operation = 'redact';
      redactionData.content_type = this.arg.data.type;
      redactionData.permanent_redaction = this.ranges_selected;
    }

    if (this.redaction) {
      redactionData.id = this.redaction.id;
      this.receiverTipService.updateRedaction(redactionData);
    } else {
      this.receiverTipService.newRedaction(redactionData);
    }

    this.cancel();
  }

}
