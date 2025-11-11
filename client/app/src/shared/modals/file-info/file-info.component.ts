import {Component, Input, OnInit, inject} from "@angular/core";
import {NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {RFile, WbFile} from "@app/models/app/shared-public-model";
import {ReceiversById} from "@app/models/receiver/receiver-tip-data";
import {DatePipe} from "@angular/common";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {ByteFmtPipe} from "@app/shared/pipes/byte-fmt.pipe";

@Component({
    selector: "src-file-info",
    templateUrl: "./file-info.component.html",
    standalone: true,
    imports: [DatePipe, TranslateModule, TranslatorPipe, ByteFmtPipe]
})
export class FileInfoComponent implements OnInit {
  private modalService = inject(NgbModal);

  @Input() file: RFile | WbFile;
  @Input() receivers_by_id: ReceiversById;

  isRFile = false;

  ngOnInit(): void {
    // Check if this is an RFile (has 'description' property) or WbFile (has 'ifile_id')
    this.isRFile = 'description' in this.file;
  }

  getHashSHA256(): string {
    // Both RFile and WbFile use 'hash_sha256'
    if ('hash_sha256' in this.file && this.file.hash_sha256) {
      return this.file.hash_sha256;
    }
    return '';
  }

  getHashSHA512(): string {
    // Both RFile and WbFile use 'hash_sha512'
    if ('hash_sha512' in this.file && this.file.hash_sha512) {
      return this.file.hash_sha512;
    }
    return '';
  }

  getDescription(): string {
    // Only RFile has description
    if (this.isRFile && 'description' in this.file) {
      return this.file.description;
    }
    return '';
  }

  cancel() {
    this.modalService.dismissAll();
  }
}

