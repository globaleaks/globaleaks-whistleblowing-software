import {AfterViewInit, Component, TemplateRef, ViewChild, ChangeDetectorRef, inject} from "@angular/core";
import {Tab} from "@app/models/component-model/tab";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {UsersTab1Component} from "@app/pages/admin/users/users-tab1/users-tab1.component";
import {UsersTab2Component} from "@app/pages/admin/users/users-tab2/users-tab2.component";
import {UserProfileComponent} from "@app/pages/admin/users/user-profile/user-profile.component";
import {NgbNav, NgbNavItem, NgbNavItemRole, NgbNavLinkButton, NgbNavLinkBase, NgbNavContent, NgbNavOutlet} from "@ng-bootstrap/ng-bootstrap";
import {NgTemplateOutlet} from "@angular/common";
import {TranslatorPipe} from "@app/shared/pipes/translate";

@Component({
    selector: "src-users",
    templateUrl: "./users.component.html",
    standalone: true,
    imports: [NgbNav, NgbNavItem, NgbNavItemRole, NgbNavLinkButton, NgbNavLinkBase, NgbNavContent, NgTemplateOutlet, NgbNavOutlet, UsersTab1Component, UsersTab2Component, UserProfileComponent, TranslatorPipe]
})
export class UsersComponent implements AfterViewInit {
  node = inject(NodeResolver);
  private cdr = inject(ChangeDetectorRef);

  @ViewChild("tab1") tab1!: TemplateRef<UsersTab1Component>;
  @ViewChild("tab2") tab2!: TemplateRef<UserProfileComponent>;
  @ViewChild("tab3") tab3!: TemplateRef<UsersTab2Component>;
  tabs: Tab[];
  nodeData: NodeResolver;
  active: string;

  ngAfterViewInit(): void {
    setTimeout(() => {
      this.active = "Users";

      this.nodeData = this.node;
      this.tabs = [
        {
          id:"users",
          title: "Users",
          component: this.tab1
        },
        {
          id:"profiles",
          title: "Profiles",
          component: this.tab2
        },
        {
          id:"options",
          title: "Options",
          component: this.tab3
        }
      ];

      this.cdr.detectChanges();
    });
  }
}