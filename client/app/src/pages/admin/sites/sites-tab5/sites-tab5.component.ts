import {Component, OnInit, inject} from "@angular/core";
import {Router} from "@angular/router";
import {FormsModule} from "@angular/forms";
import {HttpService} from "@app/shared/services/http.service";
import {exchangeConfig, exchangeMode, exchangeModel, exchangeModeSides, exchangeOwner, exchangeType, exchangeTypeLabels} from "@app/models/admin/exchange";
import {tenantResolverModel} from "@app/models/resolvers/tenant-resolver-model";
import {PaginatedInterfaceComponent} from "@app/shared/components/paginated-interface/paginated-interface.component";
import {TableHeaderComponent} from "@app/shared/components/table/table-header.component";
import {TableFilterOption, TableState} from "@app/shared/components/table/table-state";
import {TranslateModule, TranslateService} from "@ngx-translate/core";

/** The entry of the channel dropdown that declares a channel instead of naming one */
const NEW_CHANNEL = "new";

/**
 * An exchange along with what the reader sees of it: the labels are held on
 * the row, so that the columns sort, filter and search on the very words the
 * table displays.
 */
interface ExchangeRow {
  exchange: exchangeModel;
  type: exchangeType;
  mode: exchangeMode;
  type_label: string;
  mode_label: string;
  source_name: string;
  target_name: string;
  owner_name: string;
  channel_name: string;
  source?: tenantResolverModel;
  target?: tenantResolverModel;
}

@Component({
    selector: "src-sites-tab5",
    templateUrl: "./sites-tab5.component.html",
    standalone: true,
    imports: [FormsModule, PaginatedInterfaceComponent, TableHeaderComponent, TranslateModule]
})
export class SitesTab5Component implements OnInit {
  private readonly httpService = inject(HttpService);
  private readonly router = inject(Router);
  private readonly translateService = inject(TranslateService);

  sites: tenantResolverModel[] = [];
  profiles: tenantResolverModel[] = [];
  entities: tenantResolverModel[] = [];
  exchanges: exchangeModel[] = [];
  rows: ExchangeRow[] = [];

  showAddExchange = false;
  expandedId = "";

  readonly types: exchangeType[] = ["transmission", "communication"];
  readonly modes: exchangeMode[] = ["site-site", "profile-site", "site-profile", "profile-profile"];
  readonly typeLabels = exchangeTypeLabels;

  typeOptions: TableFilterOption[] = [];
  modeOptions: TableFilterOption[] = [];
  sourceOptions: TableFilterOption[] = [];
  targetOptions: TableFilterOption[] = [];

  readonly table = new TableState<ExchangeRow>({
    orderBy: "source_name",
    filters: {
      type: {type: "select"},
      mode: {type: "select"},
      source_name: {type: "select"},
      target_name: {type: "select"}
    }
  });

  // Type first; the mode decides what the pair is made of
  draft: {type: exchangeType, mode: exchangeMode | "", source: string, target: string,
          channel: string, channel_name: string} = {
    type: "transmission",
    mode: "",
    source: "",
    target: "",
    channel: "",
    channel_name: ""
  };

  // Edited on a copy: an abandoned row changes nothing
  config: exchangeConfig = {
    questionnaire: "",
    request_questionnaire: ""
  };

  // The channel is chosen here: one the destination holds, or a new one declared
  readonly newChannel = NEW_CHANNEL;

  // With an authorization demanded, a request is filed first with a questionnaire of the destination
  requestAuthorization = false;

  ngOnInit(): void {
    this.typeOptions = this.types.map(type => ({id: type, label: this.translateService.instant(this.typeLabels[type])}));
    this.modeOptions = this.modes.map(mode => ({id: mode, label: this.modeLabel(mode)}));

    this.loadTenants(() => this.loadExchanges());
  }

  private loadTenants(then?: () => void): void {
    this.httpService.fetchTenant().subscribe(tenants => {
      this.sites = tenants.filter(tenant => tenant.id < 1000001);
      this.profiles = tenants.filter(tenant => tenant.id > 1000001);
      this.entities = this.sites.concat(this.profiles);

      if (then) {
        then();
      } else {
        this.refreshRows();
      }
    });
  }

  loadExchanges(): void {
    this.httpService.requestExchanges().subscribe(exchanges => {
      this.exchanges = exchanges;
      this.refreshRows();
    });
  }

  // Related by UUID: site ids are reused, UUIDs are not
  private entityOf(uuid: string): tenantResolverModel | undefined {
    return this.entities.find(entity => entity.uuid === uuid);
  }

  private nameOf(uuid: string): string {
    const entity = this.entityOf(uuid);
    return entity ? entity.name : uuid;
  }

  /**
   * The site the reports of an exchange belong to: what a site owns lives on
   * it, with the questionnaire and the retention of its own objects.
   */
  ownerOf(exchange: exchangeModel): tenantResolverModel | undefined {
    return this.entityOf(this.ownerSide(exchange.type) === "source" ? exchange.source : exchange.target);
  }

  // The type says which side owns what is created
  ownerSide(type: exchangeType): exchangeOwner {
    return type === "communication" ? "source" : "target";
  }

  private refreshRows(): void {
    this.rows = this.exchanges.map(exchange => {
      const owner = this.ownerOf(exchange);

      return {
        exchange,
        type: exchange.type,
        mode: exchange.mode,
        type_label: this.translateService.instant(this.typeLabels[exchange.type] || exchange.type),
        mode_label: this.modeLabel(exchange.mode),
        source_name: this.nameOf(exchange.source),
        target_name: this.nameOf(exchange.target),
        owner_name: owner ? owner.name : "",
        channel_name: exchange.channel_name,
        source: this.entityOf(exchange.source),
        target: this.entityOf(exchange.target)
      };
    });

    this.updateOptions();
    this.table.setItems(this.rows);
  }

  private updateOptions(): void {
    const names = (pick: (row: ExchangeRow) => string) =>
      Array.from(new Set(this.rows.map(pick)))
           .sort((a, b) => a.localeCompare(b))
           .map(name => ({id: name, label: name}));

    this.sourceOptions = names(row => row.source_name);
    this.targetOptions = names(row => row.target_name);
  }

  // The mode is named by the two objects it relates, joined by the arrow that
  // tells which of the two files towards the other
  modeLabel(mode: exchangeMode): string {
    const sides = exchangeModeSides[mode];
    if (!sides) {
      return mode;
    }

    return this.translateService.instant(sides[0]) + " → " +
           this.translateService.instant(sides[1]);
  }

  toggleAddExchange(): void {
    this.showAddExchange = !this.showAddExchange;
    this.resetDraft();
  }

  private resetDraft(): void {
    this.draft = {type: "transmission", mode: "", source: "", target: "",
                  channel: "", channel_name: ""};
  }

  /**
   * The channels the exchange under composition may run through: the ones of
   * the destination that the exchanges run through, plus the one it declares
   * there by naming it.
   */
  draftChannels(): any[] {
    return (this.entityOf(this.draft.target)?.contexts || [])
      .filter((context: any) => context.exchange);
  }

  // Until named, the channel is nothing to establish
  declaringChannel(): boolean {
    return this.draft.channel === NEW_CHANNEL;
  }

  draftIncomplete(): boolean {
    return !this.draft.source || !this.draft.target || !this.draft.channel ||
           (this.declaringChannel() && !this.draft.channel_name.trim());
  }

  sourceCandidates(): tenantResolverModel[] {
    return this.draft.mode.startsWith("profile") ? this.profiles : this.sites;
  }

  // The origin is not among the destinations
  targetCandidates(): tenantResolverModel[] {
    const candidates = this.draft.mode.endsWith("profile") ? this.profiles : this.sites;

    return candidates.filter(entity => entity.uuid !== this.draft.source);
  }

  onTypeChange(): void {
    this.draft.source = "";
    this.onSourceChange();
  }

  onModeChange(): void {
    this.draft.source = "";
    this.onSourceChange();
  }

  onSourceChange(): void {
    this.draft.target = "";
    this.onTargetChange();
  }

  // Another destination means another choice of channel
  onTargetChange(): void {
    this.draft.channel = "";
    this.draft.channel_name = "";
  }

  addExchange(): void {
    if (!this.draft.mode || this.draftIncomplete()) {
      return;
    }

    const declaring = this.declaringChannel();

    this.httpService.requestCreateExchange({
      type: this.draft.type,
      source: this.draft.source,
      target: this.draft.target,
      channel: declaring ? "" : this.draft.channel,
      channel_name: declaring ? this.draft.channel_name.trim() : "",
      questionnaire: "",
      request_questionnaire: ""
    }).subscribe(exchange => {
      this.exchanges = [...this.exchanges.filter(entry => entry.id !== exchange.id), exchange];

      this.showAddExchange = false;
      this.resetDraft();

      // A declared channel is read back among the channels of its destination
      if (declaring) {
        this.loadTenants();
      } else {
        this.refreshRows();
      }

      this.toggleRow(this.rows.find(row => row.exchange.id === exchange.id));
    });
  }

  /**
   * The row is the handle of the exchange it displays: a click anywhere on
   * it opens the exchange, save for the elements that already carry an
   * action of their own.
   */
  onRowClick(row: ExchangeRow, event: MouseEvent): void {
    const target = event.target as HTMLElement | null;

    if (target && target.closest("a, button, input, select, textarea, label")) {
      return;
    }

    this.toggleRow(row);
  }

  toggleRow(row?: ExchangeRow): void {
    if (!row) {
      return;
    }

    if (this.expandedId === row.exchange.id) {
      this.expandedId = "";
      return;
    }

    this.expandedId = row.exchange.id;
    this.config = {
      questionnaire: row.exchange.questionnaire || "",
      request_questionnaire: row.exchange.request_questionnaire || ""
    };

    this.requestAuthorization = !!this.config.request_questionnaire;
  }

  // The authorization is demanded by naming the questionnaire of the request; the first of the
  // destination by default
  onRequestAuthorizationChange(row: ExchangeRow): void {
    if (!this.requestAuthorization) {
      this.config.request_questionnaire = "";
      return;
    }

    if (!this.config.request_questionnaire) {
      const questionnaires = this.targetQuestionnaires(row);
      this.config.request_questionnaire = questionnaires.length ? questionnaires[0].id : "";
    }
  }

  /**
   * The questionnaires the exchange may name: the ones of the side that owns
   * the reports it creates, since a questionnaire shapes what lives there.
   */
  ownerEntity(row: ExchangeRow): tenantResolverModel | undefined {
    return this.ownerSide(row.type) === "source" ? row.source : row.target;
  }

  ownerQuestionnaires(row: ExchangeRow): any[] {
    return this.ownerEntity(row)?.questionnaires || [];
  }

  targetQuestionnaires(row: ExchangeRow): any[] {
    return row.target?.questionnaires || [];
  }

  saveConfig(row: ExchangeRow): void {
    this.httpService.requestUpdateExchange(row.exchange.id, this.config).subscribe(updated => {
      Object.assign(row.exchange, updated);
      this.expandedId = "";
      this.refreshRows();
    });
  }

  /**
   * The channel is configured on the site holding it: naming it leads to the
   * card of the channel, where the recipients that take part in the exchange
   * and what lives there are decided.
   */
  configureChannel(row: ExchangeRow, event: Event): void {
    event.preventDefault();

    const channel = row.exchange.channel;

    if (!row.target || !channel) {
      return;
    }

    // A channel of this platform is reached in the open session; one of another site by entering it
    if (row.target.id === 1) {
      void this.router.navigate(["/admin/channels"], {queryParams: {id: channel}});
      return;
    }

    const destination = "/admin/channels?id=" + channel;

    this.httpService.requestTenantSwitch("api/auth/tenantauthswitch/" + row.target.id).subscribe(response => {
      window.open(response.redirect + "&redirect=" + encodeURIComponent(destination), "_blank", "noopener");
    });
  }

  removeExchange(row: ExchangeRow): void {
    this.httpService.requestDeleteExchange(row.exchange.id).subscribe(() => {
      this.exchanges = this.exchanges.filter(entry => entry.id !== row.exchange.id);

      if (this.expandedId === row.exchange.id) {
        this.expandedId = "";
      }

      // The channel departs with the last exchange: reload what the destination holds
      this.loadTenants();
    });
  }
}
