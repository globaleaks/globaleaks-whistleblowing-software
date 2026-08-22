import {ComponentFactoryResolver, Directive, ViewContainerRef, OnInit, inject, input} from "@angular/core";
import {contextResolverModel} from "@app/models/resolvers/context-resolver-model";
import {nodeResolverModel} from "@app/models/resolvers/node-resolver-model";
import {userResolverModel} from "@app/models/resolvers/user-resolver-model";
import {ImageUploadComponent} from "@app/shared/partials/image-upload/image-upload.component";

@Directive({
    selector: "[appImageUpload]",
    standalone: true,
})
export class ImageUploadDirective implements OnInit {
  private viewContainerRef = inject(ViewContainerRef);
  private componentFactoryResolver = inject(ComponentFactoryResolver);

  readonly imageUploadModel = input.required<contextResolverModel | nodeResolverModel | userResolverModel>();
  readonly imageUploadModelAttr = input.required<string>();
  readonly imageUploadId = input.required<string>();
  readonly imageSrcUrl = input<string>();

  ngOnInit() {
    const componentFactory = this.componentFactoryResolver.resolveComponentFactory(ImageUploadComponent);
    const componentRef = this.viewContainerRef.createComponent(componentFactory);
    const dynamicComponentInstance = componentRef.instance;

    dynamicComponentInstance.imageUploadModel = this.imageUploadModel();
    dynamicComponentInstance.imageUploadModelAttr = this.imageUploadModelAttr();
    dynamicComponentInstance.imageUploadId = this.imageUploadId();

  }
}
