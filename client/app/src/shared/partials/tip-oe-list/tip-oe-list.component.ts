import { Component, Input, OnInit } from "@angular/core";
import {UtilsService} from "@app/shared/services/utils.service";

@Component({
  selector: "src-tip-oe-list",
  templateUrl: "./tip-oe-list.component.html"
})
export class TipOeListComponent implements OnInit {

  collapsed = false;
  dataList: any[] = [];

  constructor(protected utils: UtilsService) {}

  ngOnInit(): void {
    this.loadData();
  }

  loadData() {
    setTimeout(() => {
      this.dataList = [
        {
          id: "uuid-1",
          organization: "Organizzazione 01",
          date: new Date(),
          files: 5,
          comments: 0,
          state: "Open"
        },
        {
          id: "uuid-2",
          organization: "Organizzazione 02",
          date: new Date(),
          files: 3,
          comments: 1,
          state: "Open"
        },
        {
          id: "uuid-3",
          organization: "Organizzazione 03",
          date: new Date(),
          files: 1,
          comments: 2,
          state: "Closed"
        }
      ];
    }, 1000); // Simula un ritardo di 1 secondo
  }
}
