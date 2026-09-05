import {Component, OnInit, inject} from "@angular/core";
import {DatePipe} from "@angular/common";
import {RouterLink} from "@angular/router";
import {NgbModal, NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {TranslateModule} from "@ngx-translate/core";
import {HttpService} from "@app/shared/services/http.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {ExchangeReportComponent} from "@app/shared/modals/exchange-report/exchange-report.component";

/**
 * One entry of what a transmitter has transmitted
 *
 * A transmission filed under a request is opened as long as the request is
 * decided: it is where the two sites talk about it. Once the report is filed,
 * and wherever a transmission is filed with no request before it, the entry is
 * opened only if the exchange left the access to the site that transmitted.
 */
interface Transmission {
  id: string;
  creation_date: string;
  tenant_name: string;
  exchange_name: string;
  type: string;
  status: string;
  rtip_id: string;
}

@Component({
  selector: "src-transmissions",
  templateUrl: "./transmissions.component.html",
  standalone: true,
  imports: [DatePipe, RouterLink, NgbTooltipModule, TranslateModule]
})
export class TransmissionsComponent implements OnInit {
  private readonly httpService = inject(HttpService);
  private readonly modalService = inject(NgbModal);
  private readonly utils = inject(UtilsService);

  transmissions: Transmission[] = [];
  available = false;
  loading = true;

  ngOnInit(): void {
    this.load();

    // Offered only where an exchange carries a transmission: elsewhere the button would only fail
    this.httpService.requestTransmitOptions().subscribe({
      next: (response: any) => {
        this.available = response.available !== false;
      },
      error: () => {
        this.available = false;
      }
    });
  }

  load(): void {
    this.loading = true;

    this.httpService.requestTransmissions().subscribe({
      next: (response: Transmission[]) => {
        this.transmissions = response;
        this.loading = false;
      },
      error: () => {
        this.transmissions = [];
        this.loading = false;
      }
    });
  }

  // Opened only where the sender keeps access: 'rtip_id' is that access, not a handle on the report
  canOpen(transmission: Transmission): boolean {
    return !!transmission.rtip_id;
  }

  // A report is addressed by its own identifier everywhere in the interface,
  // the access a recipient holds over it being a separate thing
  open(transmission: Transmission): void {
    if (!this.canOpen(transmission)) {
      return;
    }

    this.utils.go("/reports/" + transmission.id);
  }

  transmitReport(): void {
    const modalRef = this.modalService.open(ExchangeReportComponent, {
      size: 'xl',
      backdrop: 'static',
      keyboard: false
    });
    modalRef.componentInstance.title = "Transmit report";
    modalRef.result.then(
      () => this.load(),
      () => { /* dismissed */ }
    );
  }
}
