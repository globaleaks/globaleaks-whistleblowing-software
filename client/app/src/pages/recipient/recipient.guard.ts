import { Injectable } from "@angular/core";
import { ActivatedRouteSnapshot, Router, UrlTree } from "@angular/router";
import { AppDataService } from "@app/app-data.service";
import { PreferenceResolver } from "@app/shared/resolvers/preference.resolver";
import { Observable } from "rxjs";

@Injectable({
    providedIn: "root"
})
export class RecipientRoutingGuard {
    constructor(private router: Router, private preference: PreferenceResolver, private appDataService: AppDataService) {}

    canActivate(route: ActivatedRouteSnapshot): Observable<boolean | UrlTree> | Promise<boolean | UrlTree> | boolean | UrlTree {
        const isExternal = this.preference.dataModel.t_external;
    
        if (isExternal && this.appDataService.public.node.forwardings_enabled) { // TODO mode 'accreditation' - doppio controllo
            return this.router.parseUrl(`/recipient/tip-eo/${route.params["tip_id"]}`);
        } else {
            return this.router.parseUrl(`/recipient/tip/${route.params["tip_id"]}`);
        }
    }
}