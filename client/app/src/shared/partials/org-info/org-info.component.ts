import { Component, EventEmitter, Input, Output } from '@angular/core';
import { EOInfo } from '@app/models/accreditor/organization-data';
import { Constants } from "@app/shared/constants/constants";
import { NgForm } from '@angular/forms';

@Component({
  selector: 'src-org-info',
  templateUrl: './org-info.component.html'
})
export class OrgInfoComponent {

  protected readonly emailRegexp = Constants.emailRegexp;

  @Input() orgInfo: EOInfo;
  @Input() visualization: boolean = true;
  @Output() formValidityChange = new EventEmitter<boolean>();

  pecConfirmed: string;
  confirmPecTouched: boolean = false;

  checkFormValidity(form: NgForm) {
    if (!this.visualization) {
      const isValid = (form.valid ?? false) && this.checkMailsMatch();
      this.formValidityChange.emit(isValid);
    }
  }

  onConfirmPecTouched() {
    this.confirmPecTouched = true;
  }
  
  checkMailsMatch(): boolean {
    return (this.orgInfo?.organization_email ?? '') === (this.pecConfirmed ?? '')
  }

  isInvalid(control: any): boolean {
    return !this.visualization && control.invalid && control.touched;
  }

  isValid(control: any): boolean {
    return !this.visualization && control.valid && control.touched;
  }
}
