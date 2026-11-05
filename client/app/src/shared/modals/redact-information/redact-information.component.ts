import {Component, ElementRef, OnInit, inject, viewChild} from '@angular/core';
import {ReceiverTipService} from '@app/services/helper/receiver-tip.service';
import {PreferenceResolver} from '@app/shared/resolvers/preference.resolver';
import {MaskService} from '@app/shared/services/mask.service';
import {NgbModal} from '@ng-bootstrap/ng-bootstrap';
import {RedactionData} from "@app/models/component-model/redaction";

import {FormsModule} from '@angular/forms';
import {TranslatePipe} from '@ngx-translate/core';

@Component({
    selector: 'src-redact-information',
    templateUrl: './redact-information.component.html',
    standalone: true,
    imports: [
    FormsModule,
    TranslatePipe
],
})
export class RedactInformationComponent implements OnInit{
  private readonly maskService = inject(MaskService);
  protected preferenceResolver = inject(PreferenceResolver);
  private readonly modalService = inject(NgbModal);
  private readonly receiverTipService = inject(ReceiverTipService);

  readonly redactTextArea = viewChild.required<ElementRef>('redact');
  arg: any;
  redaction: any = null;
  forced_visible = false;
  vars = {
    redaction_switch: true,
  };
  ranges_selected: any
  temporary_redaction: any[] = [];
  permanent_redaction: any[] = [];
  unmaskedContent = "";
  content = "";
  originalContent = "";
  can_select = false;
  can_unselect = false;

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
    this.can_select = false;
    this.can_unselect = false;

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
    this.updateSelection();
    if (!this.can_select) {
      return;
    }

    const response:any = this.maskService.getSelectedRanges(true, this.ranges_selected,this.redactTextArea());

    if (!this.vars.redaction_switch) {
      this.ranges_selected = this.maskService.intersectRanges(this.temporary_redaction, response.new_ranges);
      this.content = this.maskService.maskContent(this.content, this.ranges_selected, true, String.fromCharCode(0x2588),"");
    } else {
      if (!this.preferenceResolver.dataModel.profile.permissions.can_mask_information) {
        this.ranges_selected = this.maskService.intersectRanges(this.temporary_redaction, response.new_ranges);
      } else {
        this.ranges_selected = response.new_ranges;
      }

      this.content = this.maskService.maskContent(this.content, this.ranges_selected, true, String.fromCharCode(0x2591),"");
      this.content = this.maskService.maskContent(this.content, this.permanent_redaction, true, String.fromCharCode(0x2588),"");
    }
    this.updateSelection();
  }

  unSelectContent() {
    this.updateSelection();
    if (!this.can_unselect) {
      return;
    }

    const response:any = this.maskService.getSelectedRanges(false, this.ranges_selected,this.redactTextArea());
    this.ranges_selected = response.new_ranges;
    this.content = this.maskService.onUnHighlight(this.content, this.vars.redaction_switch ? this.unmaskedContent : this.originalContent, [response.selected_ranges]);
    this.updateSelection();
  }

  updateSelection() {
    const elem = this.redactTextArea().nativeElement;
    const start = elem.selectionStart;
    const end = elem.selectionEnd;
    this.can_select = start < end;
    this.can_unselect = start < end && this.ranges_selected.some((range: any) => range.start < end && range.end >= start);

    if (!this.vars.redaction_switch) {
      let position = start;
      const ranges = this.temporary_redaction.slice().sort((a, b) => a.start - b.start);

      for (const range of ranges) {
        if (range.start > position) {
          break;
        }
        position = Math.max(position, range.end + 1);
      }

      this.can_select = this.can_select && position >= end;
    }
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
      this.receiverTipService.updateRedaction(redactionData, this.arg.tip.id);
    } else {
      this.receiverTipService.newRedaction(redactionData, this.arg.tip.id);
    }

    this.cancel();
  }

}
