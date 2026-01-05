import { Injectable, inject } from '@angular/core';
import { NgbModal, NgbModalRef } from '@ng-bootstrap/ng-bootstrap';
import { TipAuditLogComponent } from '@app/shared/modals/tip-audit-log/tip-audit-log.component';

export interface TipAuditLogModalOptions {
  tipId: string;
  tipData?: any;
  usersData?: any[];
  keyboard?: boolean;
  lastAccess?: string;
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
    modalRef.componentInstance.lastAccess = options.lastAccess;

    return modalRef;
  }

  /**
   * Mark the audit log as viewed for a specific tip
   * @param tipId The tip ID
   */
  markAuditLogAsViewed(tipId: string): void {
    const storageKey = `auditlog_viewed_${tipId}`;
    const now = new Date().toISOString();
    localStorage.setItem(storageKey, now);
  }

  /**
   * Get the last time the audit log was viewed for a specific tip
   * @param tipId The tip ID
   * @returns Date of last view, or null if never viewed
   */
  getLastAuditLogView(tipId: string): Date | null {
    const storageKey = `auditlog_viewed_${tipId}`;
    const stored = localStorage.getItem(storageKey);
    return stored ? new Date(stored) : null;
  }

  /**
   * Check if there are new entries since last audit log view
   * @param tipId The tip ID
   * @param tipUpdateDate The tip's update_date from backend
   * @param tipLastAccess The tip's last_access from backend
   * @returns true if there are potentially new entries
   */
  hasNewEntriesSinceLastView(tipId: string, tipUpdateDate?: string, tipLastAccess?: string): boolean {
    const lastAuditLogView = this.getLastAuditLogView(tipId);

    if (!lastAuditLogView) {
      return this.checkNewEntriesWithoutAuditView(tipUpdateDate, tipLastAccess);
    }

    return this.checkNewEntriesSinceAuditView(tipUpdateDate, lastAuditLogView);
  }

  /**
   * Check for new entries when audit log has never been viewed
   */
  private checkNewEntriesWithoutAuditView(tipUpdateDate?: string, tipLastAccess?: string): boolean {
    if (!tipLastAccess) return true;
    if (!tipUpdateDate) return false;

    const updateDate = new Date(tipUpdateDate);
    const lastAccessDate = new Date(tipLastAccess);
    return updateDate > lastAccessDate;
  }

  /**
   * Check for new entries since last audit log view
   */
  private checkNewEntriesSinceAuditView(tipUpdateDate: string | undefined, lastAuditLogView: Date): boolean {
    if (!tipUpdateDate) return false;

    const updateDate = new Date(tipUpdateDate);
    return updateDate > lastAuditLogView;
  }
}

