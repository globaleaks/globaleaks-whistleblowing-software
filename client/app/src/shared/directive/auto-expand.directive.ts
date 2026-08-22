import { Directive, ElementRef, HostListener, AfterViewInit, inject } from '@angular/core';

@Directive({
  selector: '[srcAutoExpand]'
})
export class AutoExpandDirective implements AfterViewInit {

  private el = inject(ElementRef);

  ngAfterViewInit() {
    this.adjustHeight();
  }

  @HostListener('input') onInput() {
    this.adjustHeight();
  }

  private adjustHeight(): void {
    const textarea = this.el.nativeElement as HTMLTextAreaElement;
    textarea.style.height = 'auto';
    textarea.style.height = textarea.scrollHeight + 'px';
  }
}
