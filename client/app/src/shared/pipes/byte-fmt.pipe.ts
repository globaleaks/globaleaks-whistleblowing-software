import {Pipe, PipeTransform} from "@angular/core";

@Pipe({
    name: "byteFmt",
    standalone: true
})
export class ByteFmtPipe implements PipeTransform {

  private compared: [{ str: string; val: number; }];
  isNumber = (value: string | number): boolean => typeof value === "number";
  convertToDecimal = (num: number, decimal: number): number => {
    return Math.round(num * Math.pow(10, decimal)) / (Math.pow(10, decimal));
  };

  constructor() {
    this.compared = [{str: "B", val: 1024}];
    ["KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"].forEach((el, i) => {
      this.compared.push({str: el, val: this.compared[i].val * 1024});
    });
  }

  transform(bytes: number, decimal: number): string {
    if (this.isNumber(decimal) && isFinite(decimal) && decimal % 1 === 0 && decimal >= 0 &&
      this.isNumber(bytes) && isFinite(bytes)) {
      let i = 0;
      while (i < this.compared.length - 1 && bytes >= this.compared[i].val) i++;
      bytes /= i > 0 ? this.compared[i - 1].val : 1;
      return this.convertToDecimal(bytes, decimal) + " " + this.compared[i].str;
    }
    return "NaN";
  }
}
