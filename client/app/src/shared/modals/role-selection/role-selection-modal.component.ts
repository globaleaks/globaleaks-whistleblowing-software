import { Component, Input, inject } from "@angular/core";
import { NgbActiveModal } from "@ng-bootstrap/ng-bootstrap";
import {
  NgSelectComponent,
  NgLabelTemplateDirective,
  NgOptionTemplateDirective
} from "@ng-select/ng-select";
import { FormsModule } from "@angular/forms";
import { TranslateModule } from "@ngx-translate/core";
import { TranslatorPipe } from "@app/shared/pipes/translate";
import { PreferenceResolver } from "@app/shared/resolvers/preference.resolver";

@Component({
  selector: "src-role-selection",
  templateUrl: "./role-selection-modal.component.html",
  standalone: true,
  imports: [
    NgSelectComponent,
    FormsModule,
    NgLabelTemplateDirective,
    TranslateModule,
    TranslatorPipe,
    NgOptionTemplateDirective
  ]
})
export class RoleSelectionModalComponent {
  private activeModal = inject(NgbActiveModal);
  protected preferenceResolver = inject(PreferenceResolver);

  @Input() roles: string[] = [];
  @Input() modalTitle: string;

  selectedRole = { value: '' };

  constructor() {
    this.selectedRole.value = this.preferenceResolver?.dataModel?.profile.role || '';
  }

  confirm(): void {
    this.activeModal.close(this.selectedRole);
  }

  cancel(): void {
    this.activeModal.dismiss();
  }
}
