import { Injectable } from "@angular/core";
import { BehaviorSubject, Observable } from "rxjs";
import { ErrorCodes } from "@app/models/app/error-code";
import { LanguagesSupported, Root } from "@app/models/app/public-model";

@Injectable({
  providedIn: "root"
})
export class AppDataService {
  language = "en";
  errorCodes = new ErrorCodes();
  pageTitle = "Globaleaks";
  projectTitle = "";
  header_title = "";
  page = "blank";
  languages_enabled = new Map<string, LanguagesSupported>();
  sidebar = "";
  privacy_badge_open: boolean;
  languages_supported: Map<string, LanguagesSupported>;
  connection: { tor: any };
  languages_enabled_selector: any[];
  ctx: string;
  score: number;
  receivers_by_id: any = {};
  submissionStatuses: any[];
  submission_statuses_by_id: any;
  context_id = "";
  contexts_by_id: any = {};
  questionnaires_by_id: any = {};

  private readonly showLoadingPanelSubject: BehaviorSubject<boolean> = new BehaviorSubject<boolean>(true);
  showLoadingPanel$: Observable<boolean> = this.showLoadingPanelSubject.asObservable();

  public publicSubject: BehaviorSubject<Root> = new BehaviorSubject<Root>({} as Root);
  public$: Observable<Root> = this.publicSubject.asObservable();

  updateShowLoadingPanel(newValue: boolean) {
    this.showLoadingPanelSubject.next(newValue);
  }

  get public(): Root {
    return this.publicSubject.getValue();
  }

  updatePublic(newPublic: Root) {
    this.publicSubject.next({...newPublic});
  }
}
