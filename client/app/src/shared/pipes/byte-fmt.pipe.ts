import {Pipe, PipeTransform} from "@angular/core";

const UNITS = ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"];

@Pipe({
    name: "byteFmt",
    standalone: true
})
export class ByteFmtPipe implements PipeTransform {
  isNumber = (value: string | number): boolean => typeof value === "number";
  convertToDecimal = (num: number, decimal: number): number => {
    return Math.round(num * Math.pow(10, decimal)) / (Math.pow(10, decimal));
  };

  transform(bytes: number, decimal: number): string {
    if (this.isNumber(decimal) && isFinite(decimal) && decimal % 1 === 0 && decimal >= 0 &&
      this.isNumber(bytes) && isFinite(bytes)) {
      let i = 0;
      while (i < UNITS.length - 1 && bytes >= 1024) {
        bytes /= 1024;
        i++;
      }
      return this.convertToDecimal(bytes, decimal) + " " + (UNITS[i] ?? "");
    }
    return "NaN";
  }
}
