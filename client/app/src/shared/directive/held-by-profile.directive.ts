import {Directive, ElementRef, HostBinding, OnInit, ViewContainerRef, inject, input} from "@angular/core";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {FieldActionsComponent} from "@app/shared/partials/field-actions/field-actions.component";

@Directive({
  selector: "[srcHeldByProfile]",
  standalone: true,
})
export class HeldByProfileDirective implements OnInit {
  private readonly nodeResolver = inject(NodeResolver);
  private readonly viewContainerRef = inject(ViewContainerRef);
  private readonly elementRef = inject(ElementRef);

  readonly srcHeldByProfile = input.required<string>();

  /**
   * A site naming a profile holds what the profile hands it: the control shows the inherited value
   * and does not take a new one. The site tells apart what it may write from the very list the
   * request is filtered by, so that a field is never offered and then dropped.
   */
  @HostBinding("disabled")
  get heldByProfile(): boolean {
    return this.nodeResolver.heldByProfile(this.srcHeldByProfile());
  }

  ngOnInit() {
    // The control declares which variable it writes, and the commands that decide that variable
    // follow from it: they go at the end of the line of its label, at the opposite edge, where
    // they never fall over the control and where an area of text finds them in the same place as
    // a line of one. The label is the anchor and not the group that wraps it: a group can hold
    // several fields — the roles that reach the platform without Tor — and the commands of one
    // would sit over the commands of the other.
    const actions = this.viewContainerRef.createComponent(FieldActionsComponent);
    actions.instance.key = this.srcHeldByProfile();

    const control = this.elementRef.nativeElement as HTMLElement;

    // The label of a control is written in two ways: beside it, pointing at it by name, or
    // around it, with the text in a span. The second is the way of every checkbox, and looking
    // for the first alone left the commands between the box and the words it belongs to.
    const label = control.closest("label")
      ?? (control.id
        ? document.querySelector<HTMLElement>(`label[for="${CSS.escape(control.id)}"]`)
        : null);

    // A label nobody reads is no place to put a command: there the strip stays beside the control
    if (label && !label.classList.contains("visually-hidden")) {
      label.classList.add("config-label");
      label.appendChild(actions.location.nativeElement as HTMLElement);
    }
  }
}
