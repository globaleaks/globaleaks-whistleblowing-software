import {Directive, OnDestroy, OnInit, inject, output} from "@angular/core";
import {debounceTime, Subscription} from "rxjs";
import {NgForm} from "@angular/forms";

@Directive({
    selector: "[srcNgFormChanges]",
    standalone: true
})
export class NgFormChangeDirective implements OnInit, OnDestroy {
  private readonly ngForm = inject(NgForm);


  readonly ngFormChange = output<void>();
  private formSubscription: Subscription;

  ngOnInit() {
    this.formSubscription = this.ngForm.form.valueChanges.pipe(debounceTime(150)).subscribe(() => {
      this.ngFormChange.emit();
    });
  }

  ngOnDestroy() {
    this.formSubscription.unsubscribe();
  }
}
