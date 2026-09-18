import {Directive, TemplateRef, inject, input} from "@angular/core";

/**
 * Declares one tab of a <src-tabs> container:
 *
 *   <src-tabs>
 *     <ng-template srcTab="options" title="Options" [visible]="isAdmin">
 *       <src-options></src-options>
 *     </ng-template>
 *   </src-tabs>
 *
 * `srcTab` is the stable identifier (also exposed as data-cy on the tab
 * button), `title` the translatable label, `visible` an optional condition
 * and `icon` an optional icon class rendered before the label.
 */
@Directive({
  selector: "ng-template[srcTab]",
  standalone: true
})
export class TabDirective {
  readonly id = input.required<string>({alias: "srcTab"});
  readonly title = input.required<string>();
  readonly visible = input(true);
  readonly icon = input("");
  readonly template = inject<TemplateRef<unknown>>(TemplateRef);
}
