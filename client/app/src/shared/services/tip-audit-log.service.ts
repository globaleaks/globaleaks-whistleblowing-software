import { Injectable, inject } from '@angular/core';
import { NgbModal, NgbModalRef } from '@ng-bootstrap/ng-bootstrap';
import { TipAuditLogComponent } from '@app/shared/modals/tip-audit-log/tip-audit-log.component';

export interface TipAuditLogModalOptions {
  tipId: string;
  tipData?: any;
  usersData?: any[];
  keyboard?: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class TipAuditLogService {
  private modalService = inject(NgbModal);

  /**
   * Opens the audit log modal for a specific tip
   * @param options Configuration options for the modal
   * @returns NgbModalRef reference to the opened modal
   */
  openAuditLogModal(options: TipAuditLogModalOptions): NgbModalRef {
    const modalRef = this.modalService.open(TipAuditLogComponent, {
      size: 'xl',
      backdrop: 'static',
      keyboard: options.keyboard ?? true
    });

    modalRef.componentInstance.tipId = options.tipId;
    modalRef.componentInstance.tipData = options.tipData;
    modalRef.componentInstance.usersData = options.usersData || [];

    return modalRef;
  }
}

