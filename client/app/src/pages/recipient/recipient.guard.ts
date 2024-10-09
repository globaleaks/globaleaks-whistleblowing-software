import { Injectable } from "@angular/core";
import { ActivatedRouteSnapshot, Router, UrlTree } from "@angular/router";
import { rtipResolverModel } from "@app/models/resolvers/rtips-resolver-model";
import { PreferenceResolver } from "@app/shared/resolvers/preference.resolver";
import { Observable } from "rxjs";

@Injectable({
    providedIn: "root"
})
export class RecipientRoutingGuard {
    constructor(private router: Router, private preference: PreferenceResolver) {}

    canActivate(route: ActivatedRouteSnapshot): Observable<boolean | UrlTree> | Promise<boolean | UrlTree> | boolean | UrlTree {
        const isExternal = false; //this.preference.dataModel.t_external; // TODO: Implement t_external in preference data model
    
        if (isExternal) {
            return this.router.parseUrl(`/recipient/tip-oe/${route.params["tip_id"]}`);
        } else {
            return this.router.parseUrl(`/recipient/tip/${route.params["tip_id"]}`);
        }
    }
}