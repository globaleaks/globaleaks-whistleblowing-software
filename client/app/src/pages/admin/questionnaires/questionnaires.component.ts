import {Component} from "@angular/core";
import {TabsComponent} from "@app/shared/components/tabs/tabs.component";
import {TabDirective} from "@app/shared/components/tabs/tab.directive";
import {MainComponent} from "@app/pages/admin/questionnaires/main/main.component";
import {QuestionsComponent} from "@app/pages/admin/questionnaires/questions/questions.component";

@Component({
    selector: "src-questionnaires",
    templateUrl: "./questionnaires.component.html",
    standalone: true,
    imports: [TabsComponent, TabDirective, MainComponent, QuestionsComponent]
})
export class QuestionnairesComponent {}
