import { EventEmitter } from '@angular/core';
import { MatDialogRef } from '@angular/material/dialog';

export interface PodResources {
  gpus: number;
  ram_gb: number;
  storage_gb: number;
  [key: string]: number;
}

export interface ServerResources {
  total: PodResources;
  available: PodResources;
}

export interface PodDialogData {
  serverId: string;
  serverName: string;
  serverResources: ServerResources;
  pod?: any;
  existingPods?: any[];
}

export class PodDialogBase {
  protected resourceErrors: { [key: string]: string } = {};
  protected nameError: string = '';
  protected serverResources: ServerResources;
  protected resourceFields = ['gpus', 'ram_gb', 'storage_gb'];
  protected existingPods: any[] = [];

  constructor(
    protected dialogRef: MatDialogRef<any>,
    protected data: PodDialogData
  ) {
    this.serverResources = data.serverResources;
    this.existingPods = data.existingPods || [];
  }

  protected getMaxAvailable(resource: string): number {
    // Frontend validation uses master.json data for immediate feedback
    // Backend will perform additional validation against live Kubernetes data
    return this.serverResources?.available?.[resource] || 0;
  }

  protected validateResources(resource: string, resources: PodResources) {
    const requested = resources[resource];
    const available = this.getMaxAvailable(resource);
    
    if (requested < 0) {
      this.resourceErrors[resource] = `${resource} cannot be negative`;
    } else if (requested > available) {
      this.resourceErrors[resource] = `Requested ${resource} (${requested}) exceeds available (${available})`;
    } else {
      delete this.resourceErrors[resource];
    }
  }

  protected validateAllResources(resources: PodResources) {
    this.resourceFields.forEach(resource => this.validateResources(resource, resources));
  }

  protected validatePodName(podName: string): boolean {
    const isDuplicate = this.existingPods.some(pod => pod.pod_id === podName);
    this.nameError = isDuplicate ? 'Pod name not available' : '';
    return !isDuplicate;
  }

  protected hasResourceErrors(): boolean {
    return Object.keys(this.resourceErrors).length > 0;
  }

  protected hasErrors(): boolean {
    return this.hasResourceErrors() || !!this.nameError;
  }

  protected onCancel(): void {
    this.dialogRef.close();
  }

  protected getResourceDisplayName(resource: string): string {
    switch (resource) {
      case 'gpus': return 'GPUs';
      case 'ram_gb': return 'RAM (GB)';
      case 'storage_gb': return 'Storage (GB)';
      default: return resource;
    }
  }
} 