import {CollapsibleCardComponent} from "@app/shared/components/collapsible-card/collapsible-card.component";
import { Component, OnInit, inject } from "@angular/core";
import { TranslateModule } from "@ngx-translate/core";
import { NgbModal } from "@ng-bootstrap/ng-bootstrap";
import { HttpService } from "@app/shared/services/http.service";
import { InviteComponent } from "@app/shared/modals/invite/invite.component";
import { CommonModule } from "@angular/common";
import { PaginatedInterfaceComponent } from "@app/shared/components/paginated-interface/paginated-interface.component";

@Component({
  selector: 'src-sites-tab4',
  standalone: true,
  imports: [CollapsibleCardComponent, CommonModule, PaginatedInterfaceComponent, TranslateModule],
  templateUrl: './sites-tab4.component.html'
})
export class SitesTab4Component implements OnInit {

  private httpService = inject(HttpService);
  private modalService = inject(NgbModal);

  invites: any[] = [];
  expandedRegistration: string = '';

  ngOnInit(): void {
    this.loadInvites();
  }

  loadInvites() {
    this.httpService.requestAdminInvites()
      .subscribe((res: any) => {
        this.invites = res;
      });
  }

  openInviteModal() {
    const modalRef = this.modalService.open(InviteComponent, {backdrop: 'static', keyboard: false, size: 'lg'});
    modalRef.componentInstance.confirmFunction = (invite: {organization_name: string, email: string, mail_template: string}) => {
      this.httpService.requestAdminInvite(invite).subscribe(() => {
        this.loadInvites();
      });
    };
  }

  deleteInvite(id: string) {
    this.httpService.requestDeleteAdminInvite(id).subscribe(() => {
      this.loadInvites();
    });
  }

  acceptInvite(id: string) {
    this.httpService.requestUpdateAdminInvite(id, "accept").subscribe(() => {
      this.loadInvites();
    });
  }

  denyInvite(id: string) {
    this.httpService.requestUpdateAdminInvite(id, "deny").subscribe(() => {
      this.loadInvites();
    });
  }

  toggleRegistration(registration: any) {
    this.expandedRegistration = this.expandedRegistration === registration.id ? '' : registration.id;
  }

  canAcceptOrDeny(registration: any): boolean {
    return registration.status === 'pending';
  }

  canDelete(registration: any): boolean {
    return registration.status === 'invited' || registration.status === 'denied';
  }
}
