import {Component, OnInit, computed, inject} from "@angular/core";
import {NgbActiveModal, NgbModal, NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {UsersResolver} from "@app/shared/resolvers/users.resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import {Option} from "@app/models/app/shared-public-model";
import {User} from "@app/models/resolvers/user-resolver-model";
import {NgSelectComponent, NgLabelTemplateDirective, NgOptionTemplateDirective} from "@ng-select/ng-select";
import {FormsModule} from "@angular/forms";
import {TranslateModule} from "@ngx-translate/core";
import {FilterPipe} from "@app/shared/pipes/filter.pipe";

@Component({
    selector: "src-trigger-receiver",
    templateUrl: "./trigger-receiver.component.html",
    standalone: true,
    imports: [NgbTooltipModule, NgSelectComponent, FormsModule, NgLabelTemplateDirective, NgOptionTemplateDirective, TranslateModule, FilterPipe]
})
export class TriggerReceiverComponent implements OnInit {
  private utilsService = inject(UtilsService);
  private users = inject(UsersResolver);
  private activeModal = inject(NgbActiveModal);
  private modalService = inject(NgbModal);


  arg: Option;
  confirmFunction: (data: Option) => void;

  selected: { value: []; name: string };
  readonly userData = computed(() => this.users.resource.value());
  readonly admin_receivers_by_id = computed<Record<string, User>>(() => this.utilsService.array_to_map(this.userData()));

  ngOnInit(): void {
    this.selected = {value: [], name: ""};
  }

  confirm() {
    this.confirmFunction(this.arg);
    return this.activeModal.close(this.arg);
  }

  cancel() {
    this.modalService.dismissAll();
  }

  addReceiver(item: User) {
    if (item && this.arg.trigger_receiver.indexOf(item.id) === -1) {
      this.arg.trigger_receiver.push(item.id);
    }
  }


  removeReceiver(index: number) {
    this.arg.trigger_receiver.splice(index, 1);
  }

  resetRecipients() {
    this.arg.trigger_receiver = [];
    this.modalService.dismissAll();
  }

}
