import { Component, OnInit, inject } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { TranslateModule } from "@ngx-translate/core";
import { HttpService } from "@app/shared/services/http.service";
import { CommonModule } from "@angular/common";
import { PaginatedInterfaceComponent } from "@app/shared/components/paginated-interface/paginated-interface.component";

@Component({
  selector: 'src-sites-tab4',
  standalone: true,
  imports: [CommonModule, FormsModule, PaginatedInterfaceComponent, TranslateModule],
  templateUrl: './sites-tab4.component.html'
})
export class SitesTab4Component implements OnInit {

  private httpService = inject(HttpService);

  invites: any[] = [];
  expandedRegistration: string = '';

  invite = {
    organization_name: '',
    email: ''
  };

  ngOnInit(): void {
    this.loadInvites();
  }

  loadInvites() {
    this.httpService.requestAdminInvites()
      .subscribe((res: any) => {
        this.invites = res;
      });
  }

  createInvite() {
    this.httpService.requestAdminInvite(this.invite).subscribe(() => {
      this.invite = {
        organization_name: '',
        email: ''
      };

      this.loadInvites();
    });
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
