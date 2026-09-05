import {Component, OnInit, inject} from "@angular/core";
import {ActivatedRoute} from "@angular/router";
import {HttpService} from "@app/shared/services/http.service";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-activation",
    templateUrl: "./activation.component.html",
    standalone: true,
    imports: [TranslateModule]
})
export class ActivationComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly httpService = inject(HttpService);


  ngOnInit(): void {
    this.route.queryParams.subscribe(params => {
      if ("token" in params) {
        const token = params["token"];
        this.httpService.requestSignupToken(token).subscribe();
      }
    });
  }
}
