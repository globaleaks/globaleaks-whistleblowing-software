import { ElementRef, Injectable, inject } from '@angular/core';
import {RecieverTipData} from '@app/models/reciever/reciever-tip-data';
import {WbTipData} from '@app/models/whistleblower/wb-tip-data';
import {RedactInformationComponent} from '@app/shared/modals/redact-information/redact-information.component';
import {NgbModal} from '@ng-bootstrap/ng-bootstrap';

@Injectable({
  providedIn: 'root', 
})
export class MaskService {
  private modalService = inject(NgbModal);


  getSelectedRanges(select: boolean, selected_ranges: any[],redactTextArea:ElementRef) {
    
    const elem = redactTextArea.nativeElement;
    const selectedText = elem.value.substring(elem.selectionStart, elem.selectionEnd);

    const ranges = {
      start: elem.selectionStart,
      end: elem.selectionEnd - 1,
    };

    if (selectedText.length === 0) {
      return { new_ranges: selected_ranges, selected_ranges: ranges };
    } else if (select) {
      return { new_ranges: this.mergeRanges([ranges], selected_ranges), selected_ranges: ranges };
    } else {
      return { new_ranges: this.splitRanges(ranges, selected_ranges), selected_ranges: ranges };
    }
  }

  splitRanges(range: any, ranges: any[]) {
    ranges.sort((a, b) => a.start - b.start);
    const result = [];

    for (const r of ranges) {
      if (r.end < range.start) {
        result.push(r);
      } else if (r.start > range.end) {
        result.push(r);
      } else {
        if (r.start < range.start) {
          result.push({ start: r.start, end: range.start - 1 });
        }
        if (r.end > range.end) {
          result.push({ start: range.end + 1, end: r.end });
        }
      }
    }

    return result;
  }

  mergeRanges(newRanges: any[], temporaryRanges: any[]) {
    const allRanges = newRanges.concat(temporaryRanges);
    allRanges.sort((a, b) => a.start - b.start);

    const mergedRanges = [];
    let currentRange = allRanges[0];

    for (let i = 1; i < allRanges.length; i++) {
      const nextRange = allRanges[i];

      if (currentRange.end >= nextRange.start) {
        currentRange.end = Math.max(currentRange.end, nextRange.end);
      } else {
        mergedRanges.push(currentRange);
        currentRange = nextRange;
      }
    }

    mergedRanges.push(currentRange);
    return mergedRanges;
  }

  intersectRanges(rangeList1: any[], rangeList2: any[]) {
    rangeList1.sort((a, b) => a.start - b.start);
    rangeList2.sort((a, b) => a.start - b.start);

    const intersectedRanges = [];
    let i = 0;
    let j = 0;

    while (i < rangeList1.length && j < rangeList2.length) {
      const range1 = rangeList1[i];
      const range2 = rangeList2[j];

      const start = Math.max(range1.start, range2.start);
      const end = Math.min(range1.end, range2.end);

      if (start <= end) {
        intersectedRanges.push({ start, end });
      }

      if (range1.end < range2.end) {
        i++;
      } else {
        j++;
      }
    }

    return intersectedRanges;
  }

  maskContent(content: string, ranges: any[], mask: boolean, maskCharacter: string, originalContent: string) {
    return ranges.reduce(function (markedContent, range) {
      if (mask) {
        content =
          markedContent.substring(0, range.start) +
          maskCharacter.repeat(range.end - range.start + 1) +
          markedContent.substring(range.end + 1);
      } else {
        const maskedPart = originalContent.substring(range.start, range.end + 1);
        content =
          markedContent.substring(0, range.start) +
          maskedPart +
          markedContent.substring(range.end + 1);
      }
      return content;
    }, content);
  }

  onUnHighlight(content: string, originalContent: string, ranges: any[]) {
    return this.maskContent(content, ranges, false,"", originalContent);
  }

  getRedaction(id: string, entry: string,tip:RecieverTipData | WbTipData): any {
    const redactionObjects = tip.redactions.filter((redaction:any) => {
      if(!entry){
        return redaction.reference_id === id && redaction.entry === "0";
      } else {
        return redaction.reference_id === id && redaction.entry === entry;
      }
    });

    return redactionObjects.length > 0 ? redactionObjects[0] : null;
  }

  isMasked(id: string,tip:RecieverTipData | WbTipData): boolean {
    return this.getRedaction(id, '0',tip) !== null;
  }

  refineContent(content: string, ranges: any[], code: number): string {
    const maskedText = content.split('');

    ranges.forEach((range) => {
      if (range.start >= 0 && range.start < maskedText.length && range.end >= 0) {
        for (let i = range.start; i <= range.end; i++) {
          maskedText.splice(i, 1, String.fromCharCode(code));
        }
      }
    });

    return maskedText.join('');
  }

  redactInfo(type:string, id:string, entry:string, content:string,tip:RecieverTipData | WbTipData){
    const modalRef = this.modalService.open(RedactInformationComponent, {backdrop: 'static', keyboard: false});
    modalRef.componentInstance.arg={
      tip: tip,
      redaction: this.getRedaction(id, entry,tip),
      data: { type,id,entry,content}
    };
  }

  maskingContent(id: string, index: string, value: string,tip:RecieverTipData | WbTipData): string {
    const redaction = this.getRedaction(id, index,tip);

    let maskedValue = value;

    if (redaction) {
      if (redaction.temporary_redaction.length > 0) {
        const temporaryRedactionArray = Object.values(redaction.temporary_redaction);
        temporaryRedactionArray.sort((a:any, b:any) => a.start - b.start);

        maskedValue = this.refineContent(maskedValue, temporaryRedactionArray, 0x2591);
      }

      if (redaction.permanent_redaction.length > 0) {
        const permanentRedactionArray = Object.values(redaction.permanent_redaction);
        permanentRedactionArray.sort((a:any, b:any) => a.start - b.start);

        maskedValue = this.refineContent(maskedValue, permanentRedactionArray, 0x2588);
      }
    }

    return maskedValue;
  }
}
