import {Component, HostListener, OnInit} from "@angular/core";
import {AppConfigService} from "@app/services/root/app-config.service";
import {NgbDate, NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {AppDataService} from "@app/app-data.service";
import {GrantAccessComponent} from "@app/shared/modals/grant-access/grant-access.component";
import {RevokeAccessComponent} from "@app/shared/modals/revoke-access/revoke-access.component";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {RTipsResolver} from "@app/shared/resolvers/r-tips-resolver.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {TranslateService} from "@ngx-translate/core";
import {IDropdownSettings} from "ng-multiselect-dropdown";
import {filter, orderBy} from "lodash-es";
import {TokenResource} from "@app/shared/services/token-resource.service";
import {Router} from "@angular/router";
import {rtipResolverModel, Forwarding} from "@app/models/resolvers/rtips-resolver-model";
import { Receiver} from "@app/models/reciever/reciever-tip-data";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {HttpService} from "@app/shared/services/http.service";
import {Observable, from, switchMap} from "rxjs";
import {HttpClient, HttpResponse} from "@angular/common/http";
import {formatDate} from "@angular/common";
import { preferenceResolverModel } from "@app/models/resolvers/preference-resolver-model";

@Component({
  selector: "src-tips",
  templateUrl: "./tips.component.html"
})
export class TipsComponent implements OnInit {
  search: string | undefined;
  selectedTips: string[] = [];
  filteredTips: rtipResolverModel[];
  currentPage: number = 1;
  itemsPerPage: number = 20;
  reportDateFilter: [number, number] | null = null;
  updateDateFilter: [number, number] | null = null;
  expiryDateFilter: [number, number] | null = null;
  reportDateModel: { fromDate: NgbDate | null; toDate: NgbDate | null; } | null = null;
  updateDateModel: { fromDate: NgbDate | null; toDate: NgbDate | null; } | null = null;
  expiryDateModel: { fromDate: NgbDate | null; toDate: NgbDate | null; } | null = null;
  dropdownStatusModel: { id: number; label: string; }[] = [];
  dropdownStatusData: { id: number; label: string; }[] = [];
  dropdownContextModel: { id: number; label: string; }[] = [];
  dropdownContextData: { id: number; label: string; }[] = [];
  dropdownScoreModel: { id: number; label: string; }[] = [];
  dropdownScoreData: { id: number; label: string; }[] = [];
  sortKey: string = "creation_date";
  sortReverse: boolean = true;
  channelDropdownVisible: boolean = false;
  statusDropdownVisible: boolean = false;
  scoreDropdownVisible: boolean = false;
  index: number;
  date: { year: number; month: number };
  reportDatePicker: boolean = false;
  lastUpdatePicker: boolean = false;
  expirationDatePicker: boolean = false;
  dropdownSettings: IDropdownSettings = {
    idField: "id",
    textField: "label",
    itemsShowLimit: 5,
    allowSearchFilter: true,
    selectAllText: this.translateService.instant("Select all"),
    unSelectAllText: this.translateService.instant("Deselect all"),
    searchPlaceholderText: this.translateService.instant("Search")
  };
  preferenceData: preferenceResolverModel;

  constructor(private http: HttpClient,protected authenticationService: AuthenticationService, protected httpService: HttpService, private appConfigServices: AppConfigService, private router: Router, protected RTips: RTipsResolver, protected preference: PreferenceResolver, private modalService: NgbModal, protected utils: UtilsService, protected appDataService: AppDataService, private translateService: TranslateService, private tokenResourceService: TokenResource) {

  }

  ngOnInit() {
    if (!this.RTips.dataModel) {
      this.router.navigate(["/recipient/home"]).then();
    } else {
      this.filteredTips = this.RTips.dataModel;
      this.processTips();
    }
    this.preferenceData = this.preference.dataModel;
  }

  selectAll() {
    this.selectedTips = [];
    this.filteredTips.forEach(tip => {
      if (tip.accessible) {
      this.selectedTips.push(tip.id);
      }
    });
  }

  deselectAll() {
    this.selectedTips = [];
  }

  openGrantAccessModal(): void {
    this.utils.runUserOperation("get_users_names", {}, false).subscribe({
      next: response => {
        const selectableRecipients: Receiver[] = [];
        this.appDataService.public.receivers.forEach(async (receiver: Receiver) => {
          if (receiver.id !== this.authenticationService.session.user_id) {
            selectableRecipients.push(receiver);
          }
        });
        const modalRef = this.modalService.open(GrantAccessComponent, {backdrop: 'static', keyboard: false});
        modalRef.componentInstance.usersNames = response;
        modalRef.componentInstance.selectableRecipients = selectableRecipients;
        modalRef.componentInstance.confirmFun = (receiver_id: Receiver) => {
          const req = {
            operation: "grant",
            args: {
              rtips: this.selectedTips,
              receiver: receiver_id.id
            },
          };
          this.utils.runOperation("api/recipient/operations", req.operation, req.args, true)
            .subscribe(() => {
              this.reload();
            });
        };
        modalRef.componentInstance.cancelFun = null;
      }
    });
  }

  openRevokeAccessModal() {
    this.utils.runUserOperation("get_users_names", {}, false).subscribe(
      {
        next: response => {
          const selectableRecipients: Receiver[] = [];
          this.appDataService.public.receivers.forEach(async (receiver: Receiver) => {
            if (receiver.id !== this.authenticationService.session.user_id) {
              selectableRecipients.push(receiver);
            }
          });
          const modalRef = this.modalService.open(RevokeAccessComponent, {backdrop: 'static', keyboard: false});
          modalRef.componentInstance.usersNames = response;
          modalRef.componentInstance.selectableRecipients = selectableRecipients;
          modalRef.componentInstance.confirmFun = (receiver_id: Receiver) => {
            const req = {
              operation: "revoke",
              args: {
                rtips: this.selectedTips,
                receiver: receiver_id.id
              },
            };
            this.utils.runOperation("api/recipient/operations", req.operation, req.args, true)
              .subscribe(() => {
                this.reload();
              });
          };
          modalRef.componentInstance.cancelFun = null;
        }
      }
    );
  }

  exportTips() {
    const selectedTips = this.selectedTips.slice();

    return from(this.tokenResourceService.getWithProofOfWork()).pipe(
      switchMap((token: any) => {
        return new Observable<void>((observer) => {
          let count = 0;

          const exportOneTip = (tipId: string) => {
            const url = `api/recipient/rtips/${tipId}/export?token=${token.id}:${token.answer}`;
            const newWindow = window.open(url);

            if (newWindow) {
              newWindow.onload = () => {
                count++;
                if (count === selectedTips.length) {
                  observer.complete();
                }
              };
            }
          };

          for (let i = 0; i < selectedTips.length; i++) {
            exportOneTip(selectedTips[i]);
          }
          this.appDataService.updateShowLoadingPanel(false);
        });
      })
    ).subscribe();
  }

  reload() {
    const reloadCallback = () => {
      this.RTips.reload();
    };

    this.appConfigServices.localInitialization(true, reloadCallback);
  }

  showTipDetails(id: string): void{
    this.utils.go('/recipient/reports/' + id);
  }

  tipSwitch(id: string): void {
    this.index = this.selectedTips.indexOf(id);
    if (this.index > -1) {
      this.selectedTips.splice(this.index, 1);
    } else {
      this.selectedTips.push(id);
    }
  }

  isSelected(id: string): boolean {
    return this.selectedTips.indexOf(id) !== -1;
  }

  exportTip(tipId: string) {
    this.utils.download("api/recipient/rtips/" + tipId + "/export").subscribe();
    this.appDataService.updateShowLoadingPanel(false);
  }

  actAsWhistleblower() {
    this.http.get('/api/auth/operatorauthswitch', { observe: 'response' }).subscribe(
      (response: HttpResponse<any>) => {
        if (response.status === 200) {
          window.open(window.location.origin + response.body.redirect);
        }
      },
    );
  }

  processTips() {
    const uniqueKeys: string[] = [];

    for (const tip of this.RTips.dataModel) {
      tip.context = this.appDataService.contexts_by_id[tip.context_id];
      tip.context_name = tip.context.name;
      tip.submissionStatusStr = this.translateService.instant(this.utils.getSubmissionStatusText(tip.status, tip.substatus, this.appDataService.submissionStatuses));
      if (!uniqueKeys.includes(tip.submissionStatusStr)) {
        uniqueKeys.push(tip.submissionStatusStr);
        this.dropdownStatusData.push({id: this.dropdownStatusData.length + 1, label: tip.submissionStatusStr});
      }
      if (!uniqueKeys.includes(tip.context_name)) {
        uniqueKeys.push(tip.context_name);
        this.dropdownContextData.push({id: this.dropdownContextData.length + 1, label: tip.context_name});
      }

      const scoreLabel = this.maskScore(tip.score);

      if (!uniqueKeys.includes(scoreLabel)) {
        uniqueKeys.push(scoreLabel);
        this.dropdownScoreData.push({id: this.dropdownScoreData.length + 1, label: scoreLabel});
      }
    }
  }

  maskScore(score: number) {
    if (score === 1) {
      return this.translateService.instant("Low");
    } else if (score === 2) {
      return this.translateService.instant("Medium");
    } else if (score === 3) {
      return this.translateService.instant("High");
    } else {
      return this.translateService.instant("None");
    }
  }

  onChanged(model: { id: number; label: string; }[], type: string) {
    this.processTips();
    if (model.length > 0 && type === "Score") {
      this.dropdownContextModel = [];
      this.dropdownStatusModel = [];
      this.dropdownScoreModel = model;
    }
    if (model.length > 0 && type === "Status") {
      this.dropdownContextModel = [];
      this.dropdownScoreModel = [];
      this.dropdownStatusModel = model;
    }
    if (model.length > 0 && type === "Context") {
      this.dropdownStatusModel = [];
      this.dropdownScoreModel = [];
      this.dropdownContextModel = model;
    }
    this.applyFilter();
  }

  checkFilter(filter: { id: number; label: string; }[]) {
    return filter.length > 0;
  };

  toggleChannelDropdown() {
    this.channelDropdownVisible = !this.channelDropdownVisible;
    this.statusDropdownVisible = false;
    this.scoreDropdownVisible = false;
    this.reportDatePicker = false;
    this.lastUpdatePicker = false;
    this.expirationDatePicker = false;
  }

  toggleStatusDropdown() {
    this.statusDropdownVisible = !this.statusDropdownVisible;
    this.channelDropdownVisible = false;
    this.scoreDropdownVisible = false;
    this.reportDatePicker = false;
    this.lastUpdatePicker = false;
    this.expirationDatePicker = false;
  }

  toggleScoreDropdown() {
    this.scoreDropdownVisible = !this.scoreDropdownVisible;
    this.channelDropdownVisible = false;
    this.statusDropdownVisible = false;
    this.reportDatePicker = false;
    this.lastUpdatePicker = false;
    this.expirationDatePicker = false;
  }

  onSearchChange(search: string | number | undefined) {
    search = String(search);

    if (typeof search !== "undefined") {
      this.currentPage = 1;
      this.filteredTips = this.RTips.dataModel;
      this.processTips();

      this.filteredTips = orderBy(filter(this.filteredTips, (tip) => {
        return this.utils.searchInObject(tip, search);
      }), "update_date");
    }
  }

  orderbyCast(data: rtipResolverModel[]): rtipResolverModel[] {
    return data;
  }

  onReportFilterChange(event: { fromDate: string | null; toDate: string | null }) {
    this.processTips();
    const {fromDate, toDate} = event;
    if (!fromDate && !toDate) {
      this.reportDateFilter = null;
      this.closeAllDatePickers();
    }
    if (fromDate && toDate) {
      this.reportDateFilter = [new Date(fromDate).getTime(), new Date(toDate).getTime()];
    }
    this.applyFilter();
  }

  onUpdateFilterChange(event: { fromDate: string | null; toDate: string | null }) {
    this.processTips();
    const {fromDate, toDate} = event;
    if (!fromDate && !toDate) {
      this.updateDateFilter = null;
      this.closeAllDatePickers();
    }
    if (fromDate && toDate) {
      this.updateDateFilter = [new Date(fromDate).getTime(), new Date(toDate).getTime()];
    }
    this.applyFilter();
  }

  onExpiryFilterChange(event: { fromDate: string | null; toDate: string | null }) {
    this.processTips();
    const {fromDate, toDate} = event;
    if (!fromDate && !toDate) {
      this.expiryDateFilter = null;
      this.closeAllDatePickers();
    }
    if (fromDate && toDate) {
      this.expiryDateFilter = [new Date(fromDate).getTime(), new Date(toDate).getTime()];
    }
    this.applyFilter();
  }

  applyFilter() {
    this.filteredTips = this.utils.getStaticFilter(this.RTips.dataModel, this.dropdownStatusModel, "submissionStatusStr", this.translateService);
    this.filteredTips = this.utils.getStaticFilter(this.filteredTips, this.dropdownContextModel, "context_name", this.translateService);
    this.filteredTips = this.utils.getStaticFilter(this.filteredTips, this.dropdownScoreModel, "score", this.translateService);
    this.filteredTips = this.utils.getDateFilter(this.filteredTips, this.reportDateFilter, this.updateDateFilter, this.expiryDateFilter);
  }

  @HostListener("document:click", ["$event"])
  onClick(event: MouseEvent) {
    const clickedElement = event.target as HTMLElement;
    const isContainerClicked = clickedElement.classList.contains("ngb-dtepicker-container") || clickedElement.classList.contains("dropdown-multi-select-container") ||
      clickedElement.closest(".ngb-dtepicker-container") !== null || clickedElement.closest(".dropdown-multi-select-container") !== null;
    if (!isContainerClicked) {
      this.closeAllDatePickers();
    }
  }

  closeAllDatePickers() {
    this.reportDatePicker = false;
    this.lastUpdatePicker = false;
    this.expirationDatePicker = false;
    this.scoreDropdownVisible = false;
    this.channelDropdownVisible = false;
    this.statusDropdownVisible = false;
    this.reportDatePicker = false;
    this.lastUpdatePicker = false;
    this.expirationDatePicker = false;
  }

  exportToCsv(): void {
    this.utils.generateCSV(JSON.stringify(this.getDataCsv()), 'reports',this.getDataCsvHeaders());
  }

  getDataCsv(): any[] {
    const output = [...this.filteredTips];
    return output.map(tip => ({
      id: tip.id,
      progressive: tip.progressive,
      important: tip.important,
      reportStatus: this.utils.isDatePassed(tip.reminder_date),
      context_name: tip.context_name,
      label: tip.label,
      status: tip.submissionStatusStr,
      creation_date: formatDate(tip.creation_date, 'dd-MM-yyyy HH:mm', 'en-US'),
      update_date: formatDate(tip.update_date, 'dd-MM-yyyy HH:mm', 'en-US'),
      expiration_date: formatDate(tip.expiration_date, 'dd-MM-yyyy HH:mm', 'en-US'),
      last_access: formatDate(tip.last_access, 'dd-MM-yyyy HH:mm', 'en-US'),
      comment_count: tip.comment_count,
      file_count: tip.file_count,
      subscription: tip.subscription === 0 ? 'Non sottoscritta' : tip.subscription === 1 ? 'Sottoscritta' : 'Sottoscritta successivamente',
      receiver_count: tip.receiver_count
    }));
  }

  getDataCsvHeaders(): string[] {
    return [
      'Id',
      'Sequential',
      'Important',
      'Reminder',
      'Channel',
      'Label',
      'Report Status',
      'Date of Report',
      'Last Update',
      'Expiration date',
      'Last Access',
      'Number of Comments',
      'Number of Files',
      'Subscription',
      'Number of Recipients'
    ].map(header => this.translateService.instant(header));
  }

  forwardingNames(forwardings: Forwarding[]){

    return forwardings.map(_ => _.name).join(', ');
  }
}
