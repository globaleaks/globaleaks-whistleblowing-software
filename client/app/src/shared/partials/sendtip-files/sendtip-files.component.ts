import { Component, Input, OnInit } from "@angular/core";
import { AttachmentFile, FileItem } from "@app/models/reciever/sendtip-data";

@Component({
  selector: "sendtip-files",
  templateUrl: "./sendtip-files.component.html"
})
export class SendtipFilesComponent implements OnInit {
  @Input() files: FileItem[] = [];
  @Input() selectedFiles: AttachmentFile[] = [];

  @Input() isSelectable: boolean = true;

  ngOnInit(): void {
  }

  toggleFileSelection(file: FileItem) {
    const index = this.selectedFiles.findIndex(f => f.id === file.id);
    if (index > -1) {
      this.selectedFiles.splice(index, 1);
    } else {
      this.selectedFiles.push(file);
    }
  }
}
