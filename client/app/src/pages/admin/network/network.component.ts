import {Component} from "@angular/core";
import {TabsComponent} from "@app/shared/components/tabs/tabs.component";
import {TabDirective} from "@app/shared/components/tabs/tab.directive";
import {HttpsComponent} from "@app/pages/admin/network/https/https.component";
import {TorComponent} from "@app/pages/admin/network/tor/tor.component";
import {AccessControlComponent} from "@app/pages/admin/network/access-control/access-control.component";
import {UrlRedirectsComponent} from "@app/pages/admin/network/url-redirects/url-redirects.component";

@Component({
    selector: "src-network",
    templateUrl: "./network.component.html",
    standalone: true,
    imports: [TabsComponent, TabDirective, HttpsComponent, TorComponent, AccessControlComponent, UrlRedirectsComponent]
})
export class NetworkComponent {}
