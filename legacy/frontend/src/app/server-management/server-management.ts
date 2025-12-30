import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDividerModule } from '@angular/material/divider';
import { ServerConfigDialogComponent } from '../server-config-dialog/server-config-dialog';
import { ApiConfig } from '../config/api.config';
import { interval, Subscription } from 'rxjs';
import { switchMap } from 'rxjs/operators';

export interface Server {
  id: string;
  name: string;
  type: string;
  environment: string;
  connection_coordinates: {
    method: string;
    host: string;
    port: number;
    username: string;
    kubeconfig_path: string;
    insecure_skip_tls_verify: boolean;
  };
  metadata: {
    location: string;
    environment: string;
    description: string;
    setup_method: string;
    setup_timestamp: string;
    configured_by: string;
  };
  kubeconfig_exists: boolean;
  connection_status?: 'connected' | 'disconnected' | 'testing' | 'error';
  last_test_time?: string;
  test_result?: any;
}

@Component({
  selector: 'server-management',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatDialogModule,
    MatTooltipModule,
    MatDividerModule
  ],
  template: `
    <div class="server-management">
      <!-- Header -->
      <div class="management-header">
        <div class="header-content">
          <mat-icon class="header-icon">dns</mat-icon>
          <div class="header-text">
            <h2>Server Management</h2>
            <p>Manage and monitor your configured Kubernetes servers</p>
          </div>
        </div>
        <button mat-raised-button color="primary" (click)="openServerConfigDialog()">
          <mat-icon>add</mat-icon>
          Configure New Server
        </button>
        <button mat-raised-button color="accent" (click)="testKubeconfigUpdate()" style="margin-left: 8px;">
          <mat-icon>settings</mat-icon>
          Test Kubeconfig Update
        </button>
      </div>

      <!-- Stats Cards -->
      <div class="stats-container">
        <mat-card class="stat-card">
          <div class="stat-content">
            <mat-icon class="stat-icon">dns</mat-icon>
            <div class="stat-info">
              <div class="stat-value">{{ servers.length }}</div>
              <div class="stat-label">Total Servers</div>
            </div>
          </div>
        </mat-card>
        
        <mat-card class="stat-card">
          <div class="stat-content">
            <mat-icon class="stat-icon">wifi</mat-icon>
            <div class="stat-info">
              <div class="stat-value">{{ connectedServers.length }}</div>
              <div class="stat-label">Connected</div>
            </div>
          </div>
        </mat-card>
        
        <mat-card class="stat-card">
          <div class="stat-content">
            <mat-icon class="stat-icon">error</mat-icon>
            <div class="stat-info">
              <div class="stat-value">{{ disconnectedServers.length }}</div>
              <div class="stat-label">Disconnected</div>
            </div>
          </div>
        </mat-card>
      </div>

      <!-- Servers List -->
      <div class="servers-container">
        <div class="section-header">
          <h3>Configured Servers</h3>
          <button mat-button (click)="refreshServers()" [disabled]="isLoading">
            <mat-icon>refresh</mat-icon>
            Refresh
          </button>
        </div>

        <!-- Loading State -->
        <div *ngIf="isLoading" class="loading-container">
          <mat-progress-spinner mode="indeterminate" diameter="40"></mat-progress-spinner>
          <p>Loading servers...</p>
        </div>

        <!-- Empty State -->
        <div *ngIf="!isLoading && servers.length === 0" class="empty-state">
          <mat-icon class="empty-icon">cloud_off</mat-icon>
          <h3>No Servers Configured</h3>
          <p>Get started by configuring your first Azure VM server</p>
          <button mat-raised-button color="primary" (click)="openServerConfigDialog()">
            <mat-icon>add</mat-icon>
            Configure Server
          </button>
        </div>

        <!-- Servers Grid -->
        <div *ngIf="!isLoading && servers.length > 0" class="servers-grid">
          <mat-card *ngFor="let server of servers" class="server-card" [ngClass]="{'connected': server.connection_status === 'connected', 'disconnected': server.connection_status === 'disconnected', 'error': server.connection_status === 'error'}">
            
            <!-- Server Header -->
            <div class="server-header">
              <div class="server-info">
                <div class="server-name">{{ server.name }}</div>
                <div class="server-id">{{ server.id }}</div>
              </div>
              <div class="server-actions-header">
                <div class="server-status">
                  <div class="status-indicator" [ngClass]="server.connection_status || 'unknown'">
                    <mat-icon *ngIf="server.connection_status === 'connected'">check_circle</mat-icon>
                    <mat-icon *ngIf="server.connection_status === 'disconnected'">cancel</mat-icon>
                    <mat-icon *ngIf="server.connection_status === 'error'">error</mat-icon>
                    <mat-icon *ngIf="server.connection_status === 'testing'">hourglass_empty</mat-icon>
                    <mat-icon *ngIf="!server.connection_status">help</mat-icon>
                  </div>
                  <span class="status-text">{{ getStatusText(server.connection_status) }}</span>
                </div>
                <button mat-icon-button 
                        color="warn" 
                        (click)="removeServer(server)" 
                        matTooltip="De-configure server"
                        class="deconfigure-button">
                  <mat-icon>delete</mat-icon>
                </button>
              </div>
            </div>

            <!-- Server Details -->
            <div class="server-details">
              <div class="detail-row">
                <span class="detail-label">Environment:</span>
                <mat-chip-set>
                  <mat-chip [ngClass]="server.environment">{{ server.environment }}</mat-chip>
                </mat-chip-set>
              </div>
              
              <div class="detail-row">
                <span class="detail-label">Location:</span>
                <span class="detail-value">{{ server.metadata.location || 'N/A' }}</span>
              </div>
              
              <div class="detail-row">
                <span class="detail-label">Host:</span>
                <span class="detail-value">{{ server.connection_coordinates.host || 'N/A' }}</span>
              </div>
              
              <div class="detail-row">
                <span class="detail-label">Port:</span>
                <span class="detail-value">{{ server.connection_coordinates.port || 'N/A' }}</span>
              </div>
              
              <div class="detail-row">
                <span class="detail-label">Username:</span>
                <span class="detail-value">{{ server.connection_coordinates.username || 'N/A' }}</span>
              </div>
              
              <div class="detail-row" *ngIf="server.metadata.description">
                <span class="detail-label">Description:</span>
                <span class="detail-value">{{ server.metadata.description }}</span>
              </div>
              
              <div class="detail-row" *ngIf="server.last_test_time">
                <span class="detail-label">Last Test:</span>
                <span class="detail-value">{{ formatTimestamp(server.last_test_time) }}</span>
              </div>
            </div>

            <!-- Test Results -->
            <div *ngIf="server.test_result" class="test-results">
              <mat-divider></mat-divider>
              <div class="test-result-header">
                <mat-icon>info</mat-icon>
                <span>Connection Test Results</span>
              </div>
              <div class="test-result-content">
                <div *ngIf="server.test_result.success" class="success-result">
                  <mat-icon>check_circle</mat-icon>
                  <span>{{ server.test_result.message }}</span>
                </div>
                <div *ngIf="!server.test_result.success" class="error-result">
                  <mat-icon>error</mat-icon>
                  <span>{{ server.test_result.message }}</span>
                </div>
                <pre *ngIf="server.test_result.nodes" class="nodes-output">{{ server.test_result.nodes }}</pre>
              </div>
            </div>

            <!-- Action Buttons -->
            <div class="server-actions">
              <button mat-button (click)="testServerConnection(server)" [disabled]="server.connection_status === 'testing'">
                <mat-icon *ngIf="server.connection_status !== 'testing'">wifi_tethering</mat-icon>
                <mat-progress-spinner *ngIf="server.connection_status === 'testing'" mode="indeterminate" diameter="16"></mat-progress-spinner>
                Test Connection
              </button>
              
              <button mat-button (click)="viewServerDetails(server)">
                <mat-icon>visibility</mat-icon>
                View Details
              </button>
            </div>
          </mat-card>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .server-management {
      padding: 24px;
      max-width: 1200px;
      margin: 0 auto;
    }

    .management-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 32px;
      padding-bottom: 24px;
      border-bottom: 2px solid #f0f0f0;
    }

    .header-content {
      display: flex;
      align-items: center;
      gap: 16px;
    }

    .header-icon {
      font-size: 32px;
      width: 32px;
      height: 32px;
      color: #1976d2;
    }

    .header-text h2 {
      margin: 0;
      color: #1976d2;
      font-weight: 500;
    }

    .header-text p {
      margin: 4px 0 0 0;
      color: #666;
    }

    .stats-container {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
      margin-bottom: 32px;
    }

    .stat-card {
      padding: 20px;
    }

    .stat-content {
      display: flex;
      align-items: center;
      gap: 16px;
    }

    .stat-icon {
      font-size: 32px;
      width: 32px;
      height: 32px;
      color: #1976d2;
    }

    .stat-info {
      flex: 1;
    }

    .stat-value {
      font-size: 24px;
      font-weight: 600;
      color: #1976d2;
      line-height: 1;
    }

    .stat-label {
      font-size: 14px;
      color: #666;
      margin-top: 4px;
    }

    .servers-container {
      margin-top: 32px;
    }

    .section-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
    }

    .section-header h3 {
      margin: 0;
      color: #333;
      font-weight: 500;
    }

    .loading-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 48px;
      text-align: center;
    }

    .loading-container p {
      margin: 16px 0 0 0;
      color: #666;
    }

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 48px;
      text-align: center;
    }

    .empty-icon {
      font-size: 64px;
      width: 64px;
      height: 64px;
      color: #ccc;
      margin-bottom: 16px;
    }

    .empty-state h3 {
      margin: 0 0 8px 0;
      color: #666;
    }

    .empty-state p {
      margin: 0 0 24px 0;
      color: #999;
    }

    .servers-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
      gap: 24px;
    }

    .server-card {
      padding: 24px;
      transition: all 0.3s ease;
    }

    .server-card:hover {
      transform: translateY(-2px);
      box-shadow: 0 8px 25px rgba(0,0,0,0.15);
    }

    .server-card.connected {
      border-left: 4px solid #4caf50;
    }

    .server-card.disconnected {
      border-left: 4px solid #ff9800;
    }

    .server-card.error {
      border-left: 4px solid #f44336;
    }

    .server-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 20px;
    }

    .server-actions-header {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .deconfigure-button {
      width: 32px;
      height: 32px;
      min-width: 32px;
      min-height: 32px;
      color: #f44336;
    }

    .deconfigure-button:hover {
      background-color: rgba(244, 67, 54, 0.1);
    }

    .server-name {
      font-size: 18px;
      font-weight: 500;
      color: #333;
      margin-bottom: 4px;
    }

    .server-id {
      font-size: 12px;
      color: #666;
      font-family: 'Courier New', monospace;
    }

    .server-status {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 4px;
    }

    .status-indicator {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 32px;
      height: 32px;
      border-radius: 50%;
    }

    .status-indicator.connected {
      background-color: #e8f5e8;
      color: #4caf50;
    }

    .status-indicator.disconnected {
      background-color: #fff3e0;
      color: #ff9800;
    }

    .status-indicator.error {
      background-color: #ffebee;
      color: #f44336;
    }

    .status-indicator.testing {
      background-color: #e3f2fd;
      color: #2196f3;
    }

    .status-indicator.unknown {
      background-color: #f5f5f5;
      color: #9e9e9e;
    }

    .status-text {
      font-size: 12px;
      color: #666;
      text-transform: capitalize;
    }

    .server-details {
      margin-bottom: 20px;
    }

    .detail-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
    }

    .detail-label {
      font-weight: 500;
      color: #666;
      font-size: 14px;
    }

    .detail-value {
      color: #333;
      font-size: 14px;
      text-align: right;
    }

    .test-results {
      margin-bottom: 20px;
    }

    .test-result-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 12px;
      font-weight: 500;
      color: #333;
    }

    .test-result-content {
      padding: 12px;
      background-color: #f9f9f9;
      border-radius: 4px;
    }

    .success-result, .error-result {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 8px;
    }

    .success-result {
      color: #4caf50;
    }

    .error-result {
      color: #f44336;
    }

    .nodes-output {
      background-color: #f5f5f5;
      padding: 8px;
      border-radius: 4px;
      font-family: 'Courier New', monospace;
      font-size: 12px;
      white-space: pre-wrap;
      margin: 8px 0 0 0;
      max-height: 100px;
      overflow-y: auto;
    }

    .server-actions {
      display: flex;
      gap: 8px;
      justify-content: flex-end;
    }

    .server-actions button {
      font-size: 12px;
    }

    @media (max-width: 768px) {
      .management-header {
        flex-direction: column;
        gap: 16px;
        align-items: stretch;
      }
      
      .servers-grid {
        grid-template-columns: 1fr;
      }
      
      .server-actions {
        flex-direction: column;
      }
    }
  `]
})
export class ServerManagementComponent implements OnInit, OnDestroy {
  servers: Server[] = [];
  isLoading = false;
  private refreshSubscription?: Subscription;

  constructor(
    private http: HttpClient,
    private dialog: MatDialog,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit() {
    this.loadServers();
    this.startAutoRefresh();
  }

  ngOnDestroy() {
    if (this.refreshSubscription) {
      this.refreshSubscription.unsubscribe();
    }
  }

  get connectedServers() {
    return this.servers.filter(s => s.connection_status === 'connected');
  }

  get disconnectedServers() {
    return this.servers.filter(s => s.connection_status !== 'connected');
  }

  loadServers() {
    this.isLoading = true;
    this.http.get<any>(ApiConfig.getServerConfigServersUrl())
      .subscribe({
        next: (response) => {
          // Handle both response formats: response.data.servers and response.data directly
          this.servers = response.data?.servers || response.data || [];
          this.isLoading = false;
        },
        error: (error) => {
          console.error('Failed to load servers:', error);
          this.snackBar.open('Failed to load servers', 'Close', { duration: 3000 });
          this.isLoading = false;
        }
      });
  }

  refreshServers() {
    this.loadServers();
  }

  startAutoRefresh() {
    // Get refresh interval from backend configuration
    this.http.get<any>(ApiConfig.getServerConfigRefreshConfigUrl()).subscribe({
      next: (response) => {
        const refreshInterval = response.data?.ui_refresh_interval || 5;
        const autoRefreshEnabled = response.data?.auto_refresh_enabled !== false;
        
        if (autoRefreshEnabled) {
          console.log(`Starting auto-refresh every ${refreshInterval} seconds`);
          
          // Refresh every N seconds based on backend config
          this.refreshSubscription = interval(refreshInterval * 1000)
            .pipe(switchMap(() => this.http.get<any>(ApiConfig.getServerConfigServersUrl())))
            .subscribe({
              next: (response) => {
                // Handle both response formats: response.data.servers and response.data directly
                this.servers = response.data?.servers || response.data || [];
                console.log(`Auto-refresh completed at ${new Date().toISOString()}`);
              },
              error: (error) => {
                console.error('Auto-refresh failed:', error);
              }
            });
        } else {
          console.log('Auto-refresh disabled by backend configuration');
        }
      },
      error: (error) => {
        console.error('Failed to get refresh configuration, using default 5s:', error);
        // Fallback to 5 seconds if config fetch fails
        this.refreshSubscription = interval(5000)
          .pipe(switchMap(() => this.http.get<any>(ApiConfig.getServerConfigServersUrl())))
          .subscribe({
            next: (response) => {
              this.servers = response.data?.servers || response.data || [];
            },
            error: (error) => {
              console.error('Auto-refresh failed:', error);
            }
          });
      }
    });
  }

  openServerConfigDialog() {
    const dialogRef = this.dialog.open(ServerConfigDialogComponent, {
      width: '800px',
      maxHeight: '90vh',
      disableClose: true
    });

    dialogRef.afterClosed().subscribe((result) => {
      if (result) {
        this.loadServers();
        if (result.status === 'success') {
          this.snackBar.open('Server configured successfully!', 'Close', { duration: 3000 });
        }
      }
    });
  }

  testServerConnection(server: Server) {
    server.connection_status = 'testing';
    
    this.http.post(ApiConfig.getServerConfigTestUrl(server.id), {})
      .subscribe({
        next: (response: any) => {
          server.connection_status = response.data?.connection_test?.success ? 'connected' : 'error';
          server.test_result = response.data?.connection_test;
          server.last_test_time = new Date().toISOString();
          
          if (response.data?.connection_test?.success) {
            this.snackBar.open('Connection test successful!', 'Close', { duration: 3000 });
          } else {
            this.snackBar.open('Connection test failed', 'Close', { duration: 3000 });
          }
        },
        error: (error) => {
          server.connection_status = 'error';
          server.test_result = {
            success: false,
            message: error.error?.message || 'Connection test failed'
          };
          server.last_test_time = new Date().toISOString();
          this.snackBar.open('Connection test failed', 'Close', { duration: 3000 });
        }
      });
  }

  viewServerDetails(server: Server) {
    // TODO: Implement detailed view dialog
    this.snackBar.open(`Viewing details for ${server.name}`, 'Close', { duration: 2000 });
  }

  removeServer(server: Server) {
    // Show confirmation dialog
    const confirmMessage = `Are you sure you want to remove server "${server.name}"? This will:
    • Remove the server configuration
    • Delete associated kubeconfig files
    • Update the system configuration
    
    This action cannot be undone.`;
    
    if (confirm(confirmMessage)) {
      // Show loading state
      server.connection_status = 'testing'; // Reuse this for loading state
      
      this.http.delete(ApiConfig.getServerConfigDeconfigureUrl(server.id))
        .subscribe({
          next: (response: any) => {
            // Remove server from local array
            this.servers = this.servers.filter(s => s.id !== server.id);
            
            // Show success message
            this.snackBar.open(
              `Server "${server.name}" removed successfully!`, 
              'Close', 
              { duration: 5000 }
            );
            
            // Show additional info if available
            if (response.data?.removed_files?.length > 0) {
              console.log('Removed files:', response.data.removed_files);
            }
            
            if (response.data?.remaining_servers !== undefined) {
              console.log(`Remaining servers: ${response.data.remaining_servers}`);
            }
          },
          error: (error) => {
            // Reset loading state
            server.connection_status = undefined;
            
            // Show error message
            const errorMessage = error.error?.message || 'Failed to remove server';
            this.snackBar.open(errorMessage, 'Close', { duration: 5000 });
            console.error('Failed to remove server:', error);
          }
        });
    }
  }

  getStatusText(status?: string): string {
    switch (status) {
      case 'connected': return 'Connected';
      case 'disconnected': return 'Disconnected';
      case 'testing': return 'Testing';
      case 'error': return 'Error';
      default: return 'Unknown';
    }
  }

  formatTimestamp(timestamp: string): string {
    return new Date(timestamp).toLocaleString();
  }

  testKubeconfigUpdate() {
    // Test the automated kubeconfig update functionality
    const testCredentials = {
      username: 'admin',
      password: 'test123'
    };

    this.http.post(`http://localhost:5005/api/server-config/servers/azure-vm-4-246-178-26/kubeconfig`, testCredentials)
      .subscribe({
        next: (response: any) => {
          if (response.type === 'success') {
            this.snackBar.open('✅ ' + response.message, 'Close', { duration: 3000 });
            this.loadServers(); // Refresh to show updated status
          } else {
            this.snackBar.open('❌ ' + response.message, 'Close', { duration: 5000 });
          }
        },
        error: (error) => {
          this.snackBar.open('❌ Failed to update kubeconfig: ' + (error.error?.message || error.message), 'Close', { duration: 5000 });
        }
      });
  }
} 