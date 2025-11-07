import {ComponentFactoryResolver, Directive, Input, ViewContainerRef, OnInit, inject} from "@angular/core";
import {contextResolverModel} from "@app/models/resolvers/context-resolver-model";
import {nodeResolverModel} from "@app/models/resolvers/node-resolver-model";
import {User} from "@app/models/resolvers/user-resolver-model";
import {ImageUploadComponent} from "@app/shared/partials/image-upload/image-upload.component";

@Directive({
    selector: "[appImageUpload]",
    standalone: true,
})
export class ImageUploadDirective implements OnInit {
  private viewContainerRef = inject(ViewContainerRef);
  private componentFactoryResolver = inject(ComponentFactoryResolver);

  @Input() imageUploadModel: contextResolverModel | nodeResolverModel | User;
  @Input() imageUploadModelAttr: string;
  @Input() imageUploadId: string;
  @Input() imageSrcUrl: string;

  ngOnInit() {
    const componentFactory = this.componentFactoryResolver.resolveComponentFactory(ImageUploadComponent);
    const componentRef = this.viewContainerRef.createComponent(componentFactory);
    const dynamicComponentInstance = componentRef.instance;

    dynamicComponentInstance.imageUploadModel = this.imageUploadModel;
    dynamicComponentInstance.imageUploadModelAttr = this.imageUploadModelAttr;
    dynamicComponentInstance.imageUploadId = this.imageUploadId;

  }
}
