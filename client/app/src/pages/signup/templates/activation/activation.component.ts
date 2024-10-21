import {Component, OnInit, inject} from "@angular/core";
import {ActivatedRoute} from "@angular/router";
import {HttpService} from "@app/shared/services/http.service";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";

@Component({
    selector: "src-activation",
    templateUrl: "./activation.component.html",
    standalone: true,
    imports: [TranslateModule, TranslatorPipe]
})
export class ActivationComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private httpService = inject(HttpService);


  ngOnInit(): void {
    this.route.queryParams.subscribe(params => {
      if ("token" in params) {
        const token = params["token"];
        this.httpService.requestSignupToken(token).subscribe();
      }
    });
  }
}
