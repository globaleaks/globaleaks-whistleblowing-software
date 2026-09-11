import {Directive, HostBinding, inject, input} from "@angular/core";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";

@Directive({
  selector: "[srcHeldByProfile]",
  standalone: true,
})
export class HeldByProfileDirective {
  private readonly nodeResolver = inject(NodeResolver);

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
}
