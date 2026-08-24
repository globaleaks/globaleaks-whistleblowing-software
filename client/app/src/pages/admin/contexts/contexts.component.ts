import {Component} from "@angular/core";
import {TabsComponent} from "@app/shared/components/tabs/tabs.component";
import {TabDirective} from "@app/shared/components/tabs/tab.directive";
import {ContextsTab1Component} from "@app/pages/admin/contexts/contexts-tab1/contexts-tab1.component";

@Component({
    selector: "src-contexts",
    templateUrl: "./contexts.component.html",
    standalone: true,
    imports: [TabsComponent, TabDirective, ContextsTab1Component]
})
export class ContextsComponent {}
