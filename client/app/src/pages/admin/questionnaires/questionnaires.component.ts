import {Component, TemplateRef, ViewChild, AfterViewInit, ChangeDetectorRef, inject} from "@angular/core";
import {Tab} from "@app/models/component-model/tab";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {MainComponent} from "@app/pages/admin/questionnaires/main/main.component";
import {QuestionsComponent} from "@app/pages/admin/questionnaires/questions/questions.component";
import {NgbNav, NgbNavItem, NgbNavItemRole, NgbNavLinkButton, NgbNavLinkBase, NgbNavContent, NgbNavOutlet} from "@ng-bootstrap/ng-bootstrap";
import {NgTemplateOutlet} from "@angular/common";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-questionnaires",
    templateUrl: "./questionnaires.component.html",
    standalone: true,
    imports: [NgbNav, NgbNavItem, NgbNavItemRole, NgbNavLinkButton, NgbNavLinkBase, NgbNavContent, NgTemplateOutlet, NgbNavOutlet, MainComponent, QuestionsComponent, TranslatorPipe, TranslateModule]
})
export class QuestionnairesComponent implements AfterViewInit {
  protected node = inject(NodeResolver);
  private cdr = inject(ChangeDetectorRef);

  @ViewChild("tab1") tab1!: TemplateRef<MainComponent>;
  @ViewChild("tab2") tab2!: TemplateRef<QuestionsComponent>;
  tabs: Tab[];
  nodeData: NodeResolver;
  active: string;

  ngAfterViewInit(): void {
    setTimeout(() => {
      this.active = "Questionnaires";

      this.nodeData = this.node;
      this.tabs = [
        {
          id:"questionnaires",
          title: "Questionnaires",
          component: this.tab1
        },
        {
          id:"question_templates",
          title: "Question templates",
          component: this.tab2
        },
      ];

      this.cdr.detectChanges();
    });
  }
}