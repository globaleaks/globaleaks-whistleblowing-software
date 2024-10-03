import {ComponentFactoryResolver, Directive, Input, ViewContainerRef, OnInit} from "@angular/core";
import {contextResolverModel} from "@app/models/resolvers/context-resolver-model";
import {nodeResolverModel} from "@app/models/resolvers/node-resolver-model";
import {userResolverModel} from "@app/models/resolvers/user-resolver-model";
import {ImageUploadComponent} from "@app/shared/partials/image-upload/image-upload.component";

@Directive({
  selector: "[appImageUpload]",
})
export class ImageUploadDirective implements OnInit {
  @Input() imageUploadModel: contextResolverModel | nodeResolverModel | userResolverModel;
  @Input() imageUploadModelAttr: string;
  @Input() imageUploadId: string;
  @Input() imageSrcUrl: string;

  constructor(private viewContainerRef: ViewContainerRef, private componentFactoryResolver: ComponentFactoryResolver) {
  }

  ngOnInit() {
    const componentFactory = this.componentFactoryResolver.resolveComponentFactory(ImageUploadComponent);
    const componentRef = this.viewContainerRef.createComponent(componentFactory);
    const dynamicComponentInstance = componentRef.instance;

    dynamicComponentInstance.imageUploadModel = this.imageUploadModel;
    dynamicComponentInstance.imageUploadModelAttr = this.imageUploadModelAttr;
    dynamicComponentInstance.imageUploadId = this.imageUploadId;

  }
}
