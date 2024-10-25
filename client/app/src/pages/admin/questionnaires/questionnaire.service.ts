import {Injectable} from "@angular/core";
import {BehaviorSubject, Observable} from "rxjs";

@Injectable({
  providedIn: "root"
})
export class QuestionnaireService {
  sharedData: any;

  private dataSubject = new BehaviorSubject<null>(null);

  sendData() {
    this.dataSubject.next(null);
  }

  getQuestionnairesData(): Observable<null> {
    return this.dataSubject.asObservable();
  }

  getData(): Observable<null> {
    return this.dataSubject.asObservable();
  }
}