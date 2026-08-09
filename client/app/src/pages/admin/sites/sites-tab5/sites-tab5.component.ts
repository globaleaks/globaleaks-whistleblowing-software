import {Component, OnInit, inject} from "@angular/core";
import {FormsModule} from "@angular/forms";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import {HttpService} from "@app/shared/services/http.service";
import {tenantResolverModel} from "@app/models/resolvers/tenant-resolver-model";
import {SelectionEditorComponent, SelectionEntry} from "@app/shared/components/selection-editor/selection-editor.component";
import {TranslateModule} from "@ngx-translate/core";

// One relationship under editing: the modes stand apart from the lists they
// edit, so that a custom selection can start out empty
interface RelationshipDraft {
  fromMode: string;
  fromSites: string[];
  toMode: string;
  toSites: string[];
}

@Component({
    selector: "src-sites-tab5",
    templateUrl: "./sites-tab5.component.html",
    standalone: true,
    imports: [FormsModule, SelectionEditorComponent, TranslateModule]
})
export class SitesTab5Component implements OnInit {
  private utilsService = inject(UtilsService);
  private httpService = inject(HttpService);
  protected nodeResolver = inject(NodeResolver);

  sites: tenantResolverModel[] = [];
  relationships: RelationshipDraft[] = [];

  ngOnInit(): void {
    this.httpService.fetchTenant().subscribe(tenants => {
      this.sites = tenants.filter(tenant => tenant.id < 1000001);
    });

    this.relationships = (this.nodeResolver.dataModel.forwarding_relationships || [])
      .map((relationship: any) => this.draftOf(relationship));
  }

  private draftOf(relationship: any): RelationshipDraft {
    const froms = relationship.from || [];
    const tos = relationship.to || [];

    return {
      fromMode: froms.indexOf("*") !== -1 ? "all" : "custom",
      fromSites: froms.filter((entry: string) => entry !== "*"),
      toMode: tos.indexOf("*") !== -1 ? "all" : "custom",
      toSites: tos.filter((entry: string) => entry !== "*")
    };
  }

  addRelationship(): void {
    this.relationships.push({fromMode: "all", fromSites: [], toMode: "all", toSites: []});
  }

  removeRelationship(index: number): void {
    this.relationships.splice(index, 1);
  }

  // The sites are related by their UUID: the site identifiers are assigned by
  // a counter and are reused, while the UUID is generated once and stays
  private selectionOf(uuids: string[], selected: boolean): SelectionEntry[] {
    return this.sites
      .filter(site => (uuids.indexOf(site.uuid) !== -1) === selected)
      .map(site => ({id: site.uuid, label: site.name}));
  }

  selectedOf(uuids: string[]): SelectionEntry[] {
    return this.selectionOf(uuids, true);
  }

  candidatesOf(uuids: string[]): SelectionEntry[] {
    return this.selectionOf(uuids, false);
  }

  addSite(uuids: string[], uuid: string): void {
    uuids.push(uuid);
  }

  removeSite(uuids: string[], uuid: string): void {
    const index = uuids.indexOf(uuid);
    if (index !== -1) {
      uuids.splice(index, 1);
    }
  }

  saveRelationships(): void {
    this.nodeResolver.dataModel.forwarding_relationships = this.relationships
      .map(relationship => ({
        from: relationship.fromMode === "all" ? ["*"] : relationship.fromSites,
        to: relationship.toMode === "all" ? ["*"] : relationship.toSites
      }));

    this.utilsService.update(this.nodeResolver.dataModel).subscribe();
  }

  saveReception(site: tenantResolverModel): void {
    this.httpService.requestUpdateTenantForwarding(site.id, {
      forward_channel: site.forward_channel || "",
      forward_request_channel: site.forward_request_channel || "",
      require_forward_requests: !!site.require_forward_requests,
      forward_source_access: !!site.forward_source_access
    }).subscribe();
  }
}
