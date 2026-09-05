import {Directive, ElementRef, HostListener, inject} from "@angular/core";
import {NgModel} from "@angular/forms";

@Directive({
    selector: "[srcSubdomainValidator]",
    standalone: true
})
export class SubdomainValidatorDirective {
  private readonly el = inject(ElementRef);
  private readonly ngModel = inject(NgModel);


  @HostListener("input")
  onInput() {
    let viewValue: string = this.ngModel.value;
    viewValue = viewValue.toLowerCase();
    viewValue = viewValue.replace(/[^a-z0-9-]/g, "");
    this.el.nativeElement.value = viewValue;
    this.ngModel.update.emit(viewValue);
  }
}
