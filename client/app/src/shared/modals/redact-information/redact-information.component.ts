import {Component, ElementRef, OnInit, inject, viewChild} from '@angular/core';
import {ReceiverTipService} from '@app/services/helper/receiver-tip.service';
import {HttpService} from '@app/shared/services/http.service';
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
  private maskService = inject(MaskService);
  protected preferenceResolver = inject(PreferenceResolver);
  private modalService = inject(NgbModal);
  private receiverTipService = inject(ReceiverTipService);
  private httpService = inject(HttpService);

  readonly redactTextArea = viewChild.required<ElementRef>('redact');
  arg: any;
  redaction: any = null;
  forced_visible = false;
  // The saved state: hidden content can be shown again, deleted content is gone for good
  temporary_redaction: any[] = [];
  permanent_redaction: any[] = [];
  // The state to save: the content to keep hidden and the content to delete
  hidden: any[] = [];
  deleting: any[] = [];
  unmaskedContent = "";
  content = "";
  can_hide = false;
  can_unhide = false;
  can_delete = false;
  changed = false;

  cancel() {
    this.modalService.dismissAll();
  }

  ngOnInit(): void {
    this.redaction = this.arg.redaction;

    if (this.redaction) {
      this.temporary_redaction = this.redaction.temporary_redaction;
      this.permanent_redaction = this.redaction.permanent_redaction;
    }

    this.hidden = this.copyRanges(this.temporary_redaction);
    this.unmaskedContent = this.arg.data.content;
    this.render(false);
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

    const selection = this.selection();
    this.hidden = this.maskService.mergeRanges([selection], this.hidden);
    this.render();
  }

  unhideContent() {
    if (!this.can_unhide) {
      return;
    }

    const selection = this.selection();
    this.hidden = this.maskService.splitRanges(selection, this.hidden);
    this.deleting = this.maskService.splitRanges(selection, this.deleting);
    this.render();
  }

  deleteContent() {
    if (!this.can_delete) {
      return;
    }

    const merged = this.maskService.mergeRanges([this.selection()], this.deleting);

    if (this.canDeleteDirectly()) {
      // Any content can be deleted, except what is deleted already
      this.deleting = this.permanent_redaction.reduce((ranges: any[], range: any) => this.maskService.splitRanges(range, ranges), merged);
    } else {
      // Only the saved hidden content can be deleted, within one hidden range at a time
      this.deleting = this.maskService.intersectRanges(this.copyRanges(this.temporary_redaction), merged);
    }

    this.render();
  }

  updateSelection() {
    const elem = this.redactTextArea().nativeElement;
    const start = elem.selectionStart;
    const end = elem.selectionEnd;
    const selected = start < end;

    this.can_hide = selected && !this.covers([...this.hidden, ...this.permanent_redaction], start, end);
    this.can_unhide = selected && this.hidden.some((range: any) => range.start < end && range.end >= start);
    this.can_delete = selected && !this.covers([...this.deleting, ...this.permanent_redaction], start, end) &&
      (this.canDeleteDirectly() || this.covers(this.temporary_redaction, start, end));
  }

  saveMasking() {
    const base = {
      internaltip_id: this.arg.tip.id,
      reference_id: this.arg.data.id,
      entry: this.arg.data.entry,
      content_type: this.arg.data.type,
      temporary_redaction: [],
      permanent_redaction: [],
      ...(this.redaction ? {id: this.redaction.id} : {}),
    };

    const prefs = this.preferenceResolver.dataModel;
    // The backend deletes only hidden content: what is to be deleted gets hidden first
    const hidden = this.maskService.mergeRanges(this.copyRanges(this.deleting), this.copyRanges(this.hidden));
    const mask: RedactionData | null = prefs.can_mask_information && this.differ(hidden, this.temporary_redaction) ?
      {...base, operation: 'mask', temporary_redaction: hidden} : null;
    const redact: RedactionData | null = prefs.can_redact_information && this.deleting.length ?
      {...base, operation: 'redact', permanent_redaction: this.deleting} : null;

    if (mask && redact) {
      const request = this.redaction ? this.httpService.requestUpdateRedaction(mask) : this.httpService.requestCreateRedaction(mask);
      request.subscribe((redaction: RedactionData) => {
        this.receiverTipService.updateRedaction({...redact, id: this.redaction ? this.redaction.id : redaction.id}, this.arg.tip.id);
      });
    } else if (redact) {
      this.receiverTipService.updateRedaction(redact, this.arg.tip.id);
    } else if (mask && this.redaction) {
      this.receiverTipService.updateRedaction(mask, this.arg.tip.id);
    } else if (mask) {
      this.receiverTipService.newRedaction(mask, this.arg.tip.id);
    }

    this.cancel();
  }

  private render(selection = true) {
    this.content = this.maskService.maskContent(this.unmaskedContent, this.hidden, true, String.fromCharCode(0x2591), "");
    this.content = this.maskService.maskContent(this.content, this.deleting, true, String.fromCharCode(0x2588), "");
    this.content = this.maskService.maskContent(this.content, this.permanent_redaction, true, String.fromCharCode(0x2588), "");
    this.changed = this.hiddenChanged() || this.deleting.length > 0;

    if (selection) {
      this.updateSelection();
    }
  }

  private selection() {
    const elem = this.redactTextArea().nativeElement;
    return {start: elem.selectionStart, end: elem.selectionEnd - 1};
  }

  // Whether the ranges, inclusive of their end, cover every character in [start, end)
  private covers(ranges: any[], start: number, end: number) {
    let position = start;

    for (const range of ranges.slice().sort((a, b) => a.start - b.start)) {
      if (range.start > position) {
        break;
      }
      position = Math.max(position, range.end + 1);
    }

    return position >= end;
  }

  // Who can hide can delete content not yet hidden, hiding it first on save
  private canDeleteDirectly() {
    const prefs = this.preferenceResolver.dataModel;
    return prefs.can_mask_information && prefs.can_redact_information;
  }

  private hiddenChanged() {
    return this.differ(this.hidden, this.temporary_redaction);
  }

  private differ(a: any[], b: any[]) {
    const normalize = (ranges: any[]) => JSON.stringify(this.copyRanges(ranges).sort((x, y) => x.start - y.start));
    return normalize(a) !== normalize(b);
  }

  private copyRanges(ranges: any[]) {
    return ranges.map((range: any) => ({start: range.start, end: range.end}));
  }
}
