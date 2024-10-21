import {Injectable, inject} from "@angular/core";
import {HttpClient} from "@angular/common/http";
import {CryptoService} from "@app/shared/services/crypto.service";
import {Observable, from, switchMap} from "rxjs";

@Injectable({
  providedIn: "root"
})
export class TokenResource {
  private cryptoService = inject(CryptoService);
  private http = inject(HttpClient);


  private baseUrl = "api/token/:id";

  getWithProofOfWork(): Observable<any> {
    return from(this.http.post("api/auth/token", {})).pipe(
      switchMap((response: any) => {
        const token = response;
        return this.cryptoService.proofOfWork(token.id).pipe(
          switchMap((answer: any) => {
            token.answer = answer;
            return new Observable<any>((observer) => {
              observer.next(token);
              observer.complete();
            });
          })
        );
      })
    );
  }
}
