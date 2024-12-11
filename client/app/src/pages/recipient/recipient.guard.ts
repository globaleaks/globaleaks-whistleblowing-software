import { Injectable } from "@angular/core";
import { ActivatedRouteSnapshot, Router, UrlTree } from "@angular/router";
import { AppDataService } from "@app/app-data.service";
import { Observable } from "rxjs";

@Injectable({
    providedIn: "root"
})
export class RecipientRoutingGuard {
    constructor(private router: Router, private appDataService: AppDataService) {}

    canActivate(route: ActivatedRouteSnapshot): Observable<boolean | UrlTree> | Promise<boolean | UrlTree> | boolean | UrlTree {
        const isExternal = this.appDataService.public.node.external;
    
        if (isExternal) {
            return this.router.parseUrl(`/recipient/tip-eo/${route.params["tip_id"]}`);
        } else {
            return this.router.parseUrl(`/recipient/tip/${route.params["tip_id"]}`);
        }
    }
}