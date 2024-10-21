import { Directive, EventEmitter, OnDestroy, OnInit, Output, inject } from "@angular/core";
import {debounceTime, Subscription} from "rxjs";
import {NgForm} from "@angular/forms";

@Directive({
    selector: "[ngFormChanges]",
    standalone: true
})
export class NgFormChangeDirective implements OnInit, OnDestroy {
  private ngForm = inject(NgForm);


  @Output("ngFormChange") formChange: EventEmitter<any> = new EventEmitter<any>();
  private formSubscription: Subscription;

  ngOnInit() {
    this.formSubscription = this.ngForm.form.valueChanges.pipe(debounceTime(150)).subscribe(() => {
      this.formChange.emit();
    });
  }

  ngOnDestroy() {
    this.formSubscription.unsubscribe();
  }
}
