import { Component, signal, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { HttpClient, HttpClientModule } from '@angular/common/http';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatDividerModule } from '@angular/material/divider';
import { MatDialog, MatDialogModule, MatDialogConfig } from '@angular/material/dialog';
import { AddPodDialogComponent } from './add-pod-dialog/add-pod-dialog';
import { EnvironmentVariableDialogComponent } from './environment-variable-dialog/environment-variable-dialog';

import { AlertDialogComponent } from './alert-dialog/alert-dialog';
import { ServerConfigDialogComponent } from './server-config-dialog/server-config-dialog';
import { ServerManagementComponent } from './server-management/server-management';
import { ConfirmDialogComponent, ConfirmDialogData } from './confirm-dialog/confirm-dialog';

import { MatTableModule } from '@angular/material/table';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ApiConfig } from './config/api.config';


@Component({
  selector: 'app-root',
  imports: [
    CommonModule,
    HttpClientModule,
    FormsModule,
    ReactiveFormsModule,
    MatCardModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatDividerModule,
    MatDialogModule,
    MatTableModule,
    MatIconModule,
    MatTooltipModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './app.html',
  styleUrl: './app.css',
  standalone: true
})
export class App implements OnInit, OnDestroy {
  protected readonly title = signal('frontend');

  servers: any[] = [];
  selectedServer: any = null;
  resourceIntegrityMessage: string = '';
  resourceIntegrityCheckInterval: any;
  podMessage: string = '';
  podMessageType: 'success' | 'error' | '' = '';
  azureVMStatus: string = 'unknown';
  azureVMStatusInterval: any;
  isReconnecting: boolean = false;
  isLoading: boolean = true; // Add loading state
  
  // Add caching properties
  private lastDataFetch: number = 0;
  private readonly CACHE_DURATION = 500; // 0.1 seconds cache for very responsive updates

  constructor(private http: HttpClient, private dialog: MatDialog, private cdr: ChangeDetectorRef) {
    // Validate API configuration on startup
    ApiConfig.validateConfig();
    this.fetchServers();
  }

  ngOnInit() {
    // Always fetch data immediately on page load, ignore cache
    this.fetchServersImmediate();
    
    // Start optimized polling with reduced frequency
    this.startOptimizedPolling();
  }

  ngOnDestroy() {
    if (this.resourceIntegrityCheckInterval) {
      clearInterval(this.resourceIntegrityCheckInterval);
    }
    if (this.azureVMStatusInterval) {
      clearInterval(this.azureVMStatusInterval);
    }
  }

  startOptimizedPolling() {
    // Single polling mechanism that fetches all data at once
    this.performDataRefresh();
    // Re-enable polling for automatic updates
    this.resourceIntegrityCheckInterval = setInterval(() => this.performDataRefresh(), 30000); // 30 seconds
    console.log('Polling enabled for automatic updates');
  }

  // New method for immediate data fetch (ignores cache)
  fetchServersImmediate() {
    console.log('Fetching servers immediately...');
    this.isLoading = true;
    
    this.http.get<any>(ApiConfig.getServersUrl()).subscribe({
      next: (response) => {
        // Backend returns an array directly, not wrapped in a 'servers' property
        this.servers = Array.isArray(response) ? response : (response.servers || []);
        this.lastDataFetch = Date.now();
        this.isLoading = false;
        console.log('Fetched servers immediately:', this.servers);
        console.log('Pod count:', this.servers.reduce((acc, s) => acc + (s.pods?.length || 0), 0));
        
        // Update selected server to reflect new data
        if (this.selectedServer && this.servers.length > 0) {
          console.log('Updating selected server with fresh data...');
          console.log('Current selected server ID:', this.selectedServer.id || this.selectedServer.server_id);
          
          const updatedSelectedServer = this.servers.find(s => 
            s.id === this.selectedServer.id || 
            s.server_id === this.selectedServer.server_id
          );
          
          if (updatedSelectedServer) {
            const oldPodCount = this.selectedServer.pods?.length || 0;
            this.selectedServer = updatedSelectedServer;
            const newPodCount = this.selectedServer.pods?.length || 0;
            console.log(`Updated selected server pods: ${oldPodCount} -> ${newPodCount}`);
          } else {
            // If selected server not found, use the first server
            this.selectedServer = this.servers[0];
            console.log('Selected server not found, using first server:', this.selectedServer.server_name || this.selectedServer.name);
          }
        }
        
        // Set default server if no server is currently selected
        if (this.servers.length > 0 && !this.selectedServer) {
          this.selectedServer = this.servers[0];
          console.log('Default server set:', this.selectedServer);
        }
        
        // Update status messages
        this.updateStatusMessages();
        // Force change detection to update the UI
        this.cdr.detectChanges();
      },
      error: (error) => {
        console.error('Error fetching servers:', error);
        this.isLoading = false;
        
        // Retry after 2 seconds
        setTimeout(() => {
          console.log('Retrying server fetch...');
          this.fetchServersImmediate();
        }, 2000);
      }
    });
  }

  performDataRefresh() {
    // Check if we should use cached data (but be less aggressive)
    const now = Date.now();
    if (now - this.lastDataFetch < this.CACHE_DURATION && this.servers.length > 0) {
      console.log('Using cached data for polling, skipping API call');
      return;
    }
    console.log('Performing data refresh, fetching fresh data from API');
    
    // Single API call to get all server data
    this.http.get<any>(ApiConfig.getServersUrl()).subscribe({
      next: (response) => {
        const servers = Array.isArray(response) ? response : (response.servers || []);
        this.servers = servers;
        this.lastDataFetch = now;
        
        // Update selected server to reflect new data
        if (this.selectedServer && this.servers.length > 0) {
          const updatedSelectedServer = this.servers.find(s => 
            s.id === this.selectedServer.id || 
            s.server_id === this.selectedServer.server_id
          );
          if (updatedSelectedServer) {
            this.selectedServer = updatedSelectedServer;
          }
        }
        
        // Update status messages
        this.updateStatusMessages();
        
        // Set default server if no server is currently selected
        if (this.servers.length > 0 && !this.selectedServer) {
          this.selectedServer = this.servers[0];
        }
      },
      error: (error) => {
        console.error('Error refreshing data:', error);
        this.resourceIntegrityMessage = 'Failed to refresh server data';
        this.azureVMStatus = 'connection_failed';
      }
    });
  }

  // Helper method to update status messages
  updateStatusMessages() {
    if (this.servers.length > 0) {
      const onlineServers = this.servers.filter((s: any) => s.status === 'Online' || s.status === 'online');
      if (onlineServers.length > 0) {
        this.resourceIntegrityMessage = 'Azure VM resource allocation is valid';
        this.azureVMStatus = 'connected';
      } else {
        this.resourceIntegrityMessage = 'Some servers are offline';
        this.azureVMStatus = 'server_unavailable';
      }
    } else {
      this.resourceIntegrityMessage = 'No servers available';
      this.azureVMStatus = 'connection_failed';
    }
  }

  // Keep fetchServers method for compatibility with other parts of the app
  fetchServers() {
    this.fetchServersImmediate();
  }

  deletePod(pod: any) {
    if (!this.selectedServer) return;
    
    // Show confirmation dialog
    const confirmData: ConfirmDialogData = {
      title: 'Confirm Pod Deletion',
      message: `Are you sure you want to delete pod "${pod.pod_id}" from namespace "${pod.namespace || 'default'}"? This action cannot be undone.`,
      confirmText: 'Delete Pod',
      cancelText: 'Cancel',
      type: 'danger'
    };
    
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '400px',
      data: confirmData,
      disableClose: true
    });
    
    dialogRef.afterClosed().subscribe((confirmed: boolean) => {
      if (confirmed) {
        this.performPodDeletion(pod);
      }
    });
  }
  
  private performPodDeletion(pod: any) {
    console.log('Deleting pod:', pod.pod_id, 'from server:', this.selectedServer.server_id || this.selectedServer.id);
    console.log('Current selected server pods before deletion:', this.selectedServer.pods?.length || 0);
    
    const payload = {
      server_id: this.selectedServer.server_id || this.selectedServer.id,
      PodName: pod.pod_id
    };
    console.log('Delete payload:', payload);
    
    this.http.post(ApiConfig.getDeletePodUrl(), payload).subscribe({
      next: (response: any) => {
        console.log('Delete response:', response);
        if (response.type === 'success') {
          this.showAlert(
            'success',
            'Pod Decommissioned',
            `Pod "${pod.pod_id}" has been successfully decommissioned.`
          );
          // Force immediate data refresh to show the updated pod list
          console.log('Refreshing data after successful pod deletion...');
          this.fetchServersImmediate();
          // Force change detection to update the UI
          this.cdr.detectChanges();
        } else {
          this.showAlert(
            'error',
            'Decommission Failed',
            response.message || 'An error occurred while decommissioning the pod.'
          );
          // Still refresh data to show current state
          console.log('Refreshing data after failed pod deletion...');
          this.fetchServersImmediate();
          // Force change detection to update the UI
          this.cdr.detectChanges();
        }
      },
      error: (err) => {
        const errorMsg = err?.error?.error || 'An error occurred while decommissioning the pod.';
        this.showAlert(
          'error',
          'Decommission Failed',
          `${errorMsg} Please try again or contact support if the issue persists.`
        );
      }
    });
  }

  openAddPodDialog() {
    if (!this.selectedServer) {
      this.showAlert(
        'error',
        'No Server Selected',
        'Please select a server before deploying a pod.'
      );
      return;
    }

    const dialogRef = this.dialog.open(AddPodDialogComponent, {
      width: '480px',
      data: {
        serverId: this.selectedServer.server_id || this.selectedServer.id,
        serverName: this.selectedServer.server_name || this.selectedServer.name,
        serverResources: this.selectedServer.resources,
        existingPods: this.selectedServer.pods || []
      }
    });

    dialogRef.componentInstance.podCreated.subscribe((pod: any) => {
      this.deployPod(pod, this.selectedServer.server_id || this.selectedServer.id);
    });
  }

  openServerConfigDialog() {
    const dialogRef = this.dialog.open(ServerConfigDialogComponent, {
      width: '480px',
      maxHeight: '90vh',
      disableClose: true
    });

    dialogRef.afterClosed().subscribe((result) => {
      if (result) {
        this.fetchServers();
        if (result.status === 'success') {
          this.showAlert('success', 'Success', 'Server configured successfully!');
        }
        // Always reload backend config after server changes
        this.http.post(ApiConfig.getServerConfigReconnectUrl(), {}).subscribe();
      }
    });
  }

  deployPod(podData: any, serverId: string) {
    const payload = { ...podData, server_id: serverId };
    
    // Show loading state
    this.showAlert(
      'info',
      'Creating Pod(s)',
      `Creating ${podData.replicas || 1} pod(s) in namespace "${podData.namespace || 'default'}" on server ${serverId}...`
    );
    
    this.http.post(ApiConfig.getCreatePodUrl(), payload).subscribe({
      next: (response: any) => {
        if (response.type === 'success') {
          this.showAlert(
            'success',
            'Pod(s) Created Successfully!',
            response.message || 'Pod(s) have been successfully created. You can now see them in the Pods Overview table.'
          );
        } else {
          this.showAlert(
            'error',
            'Pod Creation Failed',
            response.message || 'An error occurred while creating the pod(s).'
          );
        }
        // Force immediate data refresh to show the newly created pods
        this.fetchServersImmediate();
      },
              error: (err) => {
          const errorMsg = err?.error?.error || err?.error?.message || 'An error occurred during pod creation.';
          this.showAlert(
            'error',
            'Pod Creation Failed',
            `${errorMsg} Please check the server resources and try again.`
          );
        }
    });
  }

  openEnvironmentVariableDialog(pod: any): void {
    const dialogRef = this.dialog.open(EnvironmentVariableDialogComponent, {
      width: '400px',
      data: { 
        environmentVariable: pod.environmentVariable || ''
      }
    });

    dialogRef.afterClosed().subscribe((result) => {
      if (result) {
        this.setEnvironmentVariable(pod, result);
      }
    });
  }

  setEnvironmentVariable(pod: any, environmentVariable: string) {
    // For now, just show a success message
    // In a real implementation, you would send this to the backend
    this.showAlert(
      'success',
      'Environment Variable Set',
      `Environment variable "${environmentVariable}" has been set for pod "${pod.pod_id}"`
    );
  }

  compareServers = (a: any, b: any) => a && b && a.id === b.id;

  get totalServers() {
    return this.servers.length;
  }

  get totalPods() {
    return this.servers.reduce((acc: number, s: any) => acc + (s.pods?.length || 0), 0);
  }

  get totalCPUs() {
    return this.servers.reduce((acc: number, s: any) => acc + (s.resources?.total?.cpus || 0), 0);
  }

  get allocatedCPUs() {
    return Math.round(Math.max(
      0,
      this.servers.reduce((acc: number, s: any) => acc + ((s.resources?.total?.cpus || 0) - (s.resources?.available?.cpus || 0)), 0)
    ) * 100) / 100;
  }

  get actualCPUUsage() {
    return Math.round(this.servers.reduce((acc: number, s: any) => acc + (s.resources?.actual_usage?.cpus || 0), 0) * 100) / 100;
  }

  get totalGPUs() {
    return this.servers.reduce((acc: number, s: any) => acc + (s.resources?.total?.gpus || 0), 0);
  }

  get allocatedGPUs() {
    return Math.max(
      0,
      this.servers.reduce((acc: number, s: any) => acc + ((s.resources?.total?.gpus || 0) - (s.resources?.available?.gpus || 0)), 0)
    );
  }

  get actualGPUUsage() {
    return this.servers.reduce((acc: number, s: any) => acc + (s.resources?.actual_usage?.gpus || 0), 0);
  }

  get totalRAM() {
    return this.servers.reduce((acc: number, s: any) => acc + (s.resources?.total?.ram_gb || 0), 0);
  }

  get allocatedRAM() {
    return Math.round(Math.max(
      0,
      this.servers.reduce((acc: number, s: any) => acc + ((s.resources?.total?.ram_gb || 0) - (s.resources?.available?.ram_gb || 0)), 0)
    ) * 100) / 100;
  }

  get actualRAMUsage() {
    return Math.round(this.servers.reduce((acc: number, s: any) => acc + (s.resources?.actual_usage?.ram_gb || 0), 0) * 100) / 100;
  }

  get allPods() {
    // Return pods only from the selected server
    if (!this.selectedServer) {
      return [];
    }
    
    const pods = this.selectedServer.pods || [];
    console.log('allPods getter - selected server:', this.selectedServer.server_name || this.selectedServer.name);
    console.log('allPods getter - pod count:', pods.length);
    console.log('allPods getter - pods:', pods.map((p: any) => ({ pod_id: p.pod_id, status: p.status })));
    
    // Get pods from the selected server and add serverName property
    return pods.map((p: any) => ({ 
      ...p, 
      serverName: this.selectedServer.server_name || this.selectedServer.name 
    }));
  }

  get formattedPodMessage(): string {
    return this.podMessage
      ? this.podMessage.replace(/\n/g, '<br>')
      : '';
  }

  onResourceIntegrityLedClick() {
    // Handle unknown/empty resource integrity message
    if (!this.resourceIntegrityMessage) {
      this.showAlert(
        'info',
        'Resource Integrity Status',
        'Resource integrity status is unknown. Checking now...'
      );
      this.performDataRefresh();
      return;
    }
    
    // Determine alert type based on resource integrity message
    const isError = this.resourceIntegrityMessage?.toLowerCase().includes('error') || 
                   this.resourceIntegrityMessage?.toLowerCase().includes('failed') ||
                   this.resourceIntegrityMessage?.toLowerCase().includes('invalid');
    const alertType = isError ? 'error' : 'success';
    
    // Show the resource integrity message in a snackbar
    this.showAlert(
      alertType,
      'Resource Integrity Status',
      this.resourceIntegrityMessage
    );
    // Trigger a new data refresh immediately
    this.performDataRefresh();
  }

  onAzureVMStatusClick() {
    // Handle unknown Azure VM status
    if (!this.azureVMStatus || this.azureVMStatus === 'unknown') {
      this.showAlert(
        'info',
        'Azure VM Status',
        'Azure VM status is unknown. Checking now...'
      );
      this.performDataRefresh();
      return;
    }
    
    // Get detailed Azure VM connection information
    this.http.get<any[]>(ApiConfig.getServersUrl()).subscribe({
      next: (response) => {
        if (response && response.length > 0) {
          const server = response[0];
          const status = server.status || 'unknown';
          const location = server.metadata?.location || server.ip || 'Unknown location';
          const pods = server.pods?.length || 0;
          
          let alertType: 'success' | 'error' | 'info' = 'info';
          if (status === 'Online' || status === 'online') {
            alertType = 'success';
          } else {
            alertType = 'error';
          }
          
          const details = `Server: ${server.server_name || server.name}\nLocation: ${location}\nStatus: ${status}\nActive Pods: ${pods}`;
          
          this.showAlert(
            alertType,
            'Azure VM Connection Status',
            details
          );
        } else {
          this.showAlert(
            'error',
            'Azure VM Connection Failed',
            'No servers found. Please check your Azure VM configuration and network connectivity.'
          );
        }
      },
      error: (err) => {
        this.showAlert(
          'error',
          'Azure VM Connection Failed',
          'Unable to connect to Azure VM. Please check:\n\n• Network connectivity\n• Azure VM is running\n• Kubeconfig is properly configured\n• Backend service is accessible'
        );
      }
    });
  }

  onServerStatusClick(server: any) {
    const status = server.status || 'Online';
    const serverName = server.server_name || server.name || 'Unknown Server';
    const location = server.metadata?.location || server.ip || 'Unknown location';
    const pods = server.pods?.length || 0;
    
    let alertType: 'success' | 'error' | 'info' = 'info';
    if (status === 'Online' || status === 'online') {
      alertType = 'success';
    } else {
      alertType = 'error';
    }
    
    const details = `Server: ${serverName}\nLocation: ${location}\nStatus: ${status}\nActive Pods: ${pods}`;
    
    this.showAlert(
      alertType,
      'Server Connection Status',
      details
    );
  }

  showAlert(type: 'success' | 'error' | 'info', title: string, message: string, details?: string[]) {
    const dialogRef = this.dialog.open(AlertDialogComponent, {
      data: { type, title, message, details },
      position: { top: '40px' }
    });

    // Auto-dismiss after 5 seconds
    setTimeout(() => {
      if (dialogRef.componentInstance) {
        dialogRef.close();
      }
    }, 5000);
  }

  // Helper functions for pod status
  getStatusColor(status: string): string {
    const statusColors: { [key: string]: string } = {
      'online': 'status-success',
      'starting': 'status-success',
      'pending': 'status-pending',
      'in-progress': 'status-progress',
      'updating': 'status-progress',
      'failed': 'status-error',
      'error': 'status-error',
      'timeout': 'status-error',
      'unknown': 'status-unknown'
    };
    return statusColors[status] || 'status-unknown';
  }

  getStatusIcon(status: string): string {
    const statusIcons: { [key: string]: string } = {
      'online': 'check_circle',
      'starting': 'hourglass_empty',
      'pending': 'schedule',
      'in-progress': 'sync',
      'updating': 'update',
      'failed': 'error',
      'error': 'error_outline',
      'timeout': 'schedule',
      'unknown': 'help_outline'
    };
    return statusIcons[status] || 'help_outline';
  }

  getStatusDisplayName(status: string): string {
    const statusNames: { [key: string]: string } = {
      'online': 'Online',
      'starting': 'Starting',
      'pending': 'Pending',
      'in-progress': 'In Progress',
      'updating': 'Updating',
      'failed': 'Failed',
      'error': 'Error',
      'timeout': 'Timeout',
      'unknown': 'Unknown'
    };
    return statusNames[status] || 'Unknown';
  }



  selectServer(server: any) {
    // Set the selected server
    this.selectedServer = server;
    console.log('Selected server:', server);
    
    // No popup - just silently select the server
  }

  // Method to get the default server (first server in the list)
  getDefaultServer(): any {
    return this.servers.length > 0 ? this.servers[0] : null;
  }

  // Method to check if a server is the default server
  isDefaultServer(server: any): boolean {
    return this.servers.length > 0 && 
           (server.server_id === this.servers[0].server_id || server.id === this.servers[0].id);
  }

  deconfigureServer(server: any) {
    // Show confirmation dialog
    const confirmMessage = `Are you sure you want to de-configure server "${server.server_name || server.name}"? This will:
    • Remove the server configuration
    • Delete associated kubeconfig files
    • Update the system configuration
    
    This action cannot be undone.`;
    
    if (confirm(confirmMessage)) {
      const serverId = server.server_id || server.id;
      
      // Debug: Log the server object and ID being used
      console.log('De-configuring server object:', server);
      console.log('Server ID being used:', serverId);
      
      this.http.delete(ApiConfig.getServerConfigDeconfigureUrl(serverId))
        .subscribe({
          next: (response: any) => {
            // Show success message
            this.showAlert(
              'success',
              'Server De-configured',
              `Server "${server.server_name || server.name}" has been successfully de-configured and removed from the system.`
            );
            
            // Show additional info if available
            if (response.data?.removed_files?.length > 0) {
              console.log('Removed files:', response.data.removed_files);
            }
            
            if (response.data?.remaining_servers !== undefined) {
              console.log(`Remaining servers: ${response.data.remaining_servers}`);
            }
            
            // Refresh the server list from backend
            this.fetchServers();
          },
          error: (error) => {
            // Show error message
            const errorMessage = error.error?.message || 'Failed to de-configure server';
            this.showAlert(
              'error',
              'De-configuration Failed',
              errorMessage
            );
            console.error('Failed to de-configure server:', error);
          }
        });
    }
  }

  reconnectServer(server: any) {
    this.isReconnecting = true;
    // Only send required fields for reconnection
    const payload = {
      id: server.server_id || server.id,
      name: server.server_name || server.name,
      type: server.type,
      environment: server.environment,
      connection_coordinates: server.connection_coordinates || server.connection_coordinates,
    };
    this.http.post(ApiConfig.getServerConfigReconnectUrl(), payload)
      .subscribe({
        next: (response: any) => {
          this.isReconnecting = false;
          this.showAlert(
            'success',
            'Server Reconnected',
            `Server "${payload.name}" has been reconnected.`
          );
          this.fetchServers();
        },
        error: (error) => {
          this.isReconnecting = false;
          const errorMessage = error.error?.message || 'Failed to reconnect server';
          this.showAlert(
            'error',
            'Reconnection Failed',
            errorMessage
          );
        }
      });
  }
}
