import { Component, Input, inject, OnInit } from "@angular/core";
import { NgbActiveModal } from "@ng-bootstrap/ng-bootstrap";
import { NgSelectComponent } from "@ng-select/ng-select";
import { FormsModule } from "@angular/forms";
import { TranslateModule } from "@ngx-translate/core";
import { AuthenticationService } from "@app/services/helper/authentication.service";

@Component({
  selector: "src-role-selection",
  templateUrl: "./role-selection-modal.component.html",
  standalone: true,
  imports: [
    NgSelectComponent,
    FormsModule,
    TranslateModule
  ]
})
export class RoleSelectionModalComponent implements OnInit {
  private activeModal = inject(NgbActiveModal);
  protected authenticationService = inject(AuthenticationService);

  @Input() roles: { value: string; role: string }[] = [];
  @Input() modalTitle: string;

  selectedRole = { value: '' };
  selectableRoles: { value: string; role: string }[] = [];

  ngOnInit(): void {
    this.selectedRole.value = this.authenticationService.session.role;

    this.selectableRoles = this.roles.filter(
      r => r.value !== this.authenticationService.session.role
    );
  }

  confirm(): void {
    this.activeModal.close(this.selectedRole);
  }

  cancel(): void {
    this.activeModal.dismiss();
  }
}
