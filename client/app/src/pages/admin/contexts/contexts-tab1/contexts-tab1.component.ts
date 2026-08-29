import {Component, computed, inject} from "@angular/core";
import {TranslatePipe} from "@ngx-translate/core";
import {NewContext} from "@app/models/admin/new-context";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {ContextsResolver} from "@app/shared/resolvers/contexts.resolver";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {HttpService} from "@app/shared/services/http.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {FormsModule} from "@angular/forms";
import {ContextEditorComponent} from "../context-editor/context-editor.component";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {PaginatedInterfaceComponent} from "@app/shared/components/paginated-interface/paginated-interface.component";


@Component({
    selector: "src-contexts-tab1",
    templateUrl: "./contexts-tab1.component.html",
    standalone: true,
    imports: [TranslatePipe, ContextEditorComponent, FormsModule, NgbTooltipModule, PaginatedInterfaceComponent]
})
export class ContextsTab1Component {
  protected preference = inject(PreferenceResolver);
  protected httpService = inject(HttpService);
  protected authenticationService = inject(AuthenticationService);
  protected node = inject(NodeResolver);
  protected contexts = inject(ContextsResolver);
  protected utilsService = inject(UtilsService);

  showAddContext = false;
  new_context: { name: string; } = {name: ""};
  readonly contextsData = computed(() => this.contexts.resource.value());

  toggleAddContext() {
    this.showAddContext = !this.showAddContext;
  };

  addContext() {
    const context: NewContext = new NewContext();
    context.name = this.new_context.name;
    context.questionnaire_id = "default";
    context.order = this.newItemOrder(this.contextsData(), "order");
    this.utilsService.addAdminContext(context).subscribe(res => {
      this.contexts.resource.update(contexts => [...contexts, res]);
      this.new_context.name = "";
    });
  }

  newItemOrder(objects: any[], key: string): number {
    if (objects.length === 0) {
      return 0;
    }

    let max = 0;
    for (const object of objects) {
      if (object[key] > max) {
        max = object[key];
      }
    }

    return max + 1;
  }

  swap(index: number, n: number): void {
    const target = index + n;

    if (target < 0 || target >= this.contextsData().length) {
      return;
    }

    const updated = [...this.contextsData()];

    [updated[index], updated[target]] =
      [updated[target], updated[index]];

    this.contexts.resource.set(updated);

    this.httpService.requestReorderAdminContexts({
      operation: "order_elements",
      args: { ids: updated.map(c => c.id) },
    }).subscribe();
  }

  onDelete(id: string) {
   this.contexts.resource.update(contexts => contexts.filter(context => context.id !== id));
  }
}
