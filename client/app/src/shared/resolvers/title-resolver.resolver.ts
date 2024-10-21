import {Injectable, inject} from "@angular/core";
import {ActivatedRouteSnapshot} from "@angular/router";
import {Title} from "@angular/platform-browser";

@Injectable({
  providedIn: "root",
})
export class TitleResolver {
  private titleService = inject(Title);


  resolve(route: ActivatedRouteSnapshot): void {
    const title = route.data["title"] || "Globaleaks";
    this.titleService.setTitle(title);
  }
}
