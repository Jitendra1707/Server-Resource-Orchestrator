import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDividerModule } from '@angular/material/divider';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { HttpClient } from '@angular/common/http';
import { ApiConfig } from '../config/api.config';

export interface ServerConfigData {
  vm_ip?: string;
  username?: string;
  password?: string;
  name?: string;
  environment?: string;
  location?: string;
  description?: string;
  configured_by?: string;
}

@Component({
  selector: 'server-config-dialog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatCardModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatDividerModule,
    MatChipsModule,
    MatTooltipModule
  ],
  template: `
    <div class="server-config-dialog">
      <!-- Header -->
      <div class="dialog-header">
        <div class="header-content">
          <div class="header-text">
            <div class="title-row">
              <h2 mat-dialog-title>Configure Azure VM Server</h2>
              <button mat-icon-button (click)="toggleInfo()" class="info-button" matTooltip="What happens next?">
                <mat-icon>info</mat-icon>
              </button>
            </div>
            <p class="header-subtitle">Connect to a Kubernetes cluster on Azure VM</p>
          </div>
        </div>
        <button mat-icon-button (click)="onCancel()" class="close-button">
          <mat-icon>close</mat-icon>
        </button>
      </div>

      <!-- Progress Indicator -->
      <div *ngIf="isConfiguring" class="progress-container">
        <mat-progress-spinner mode="indeterminate" diameter="40"></mat-progress-spinner>
        <div class="progress-text">
          <h3>Configuring Server...</h3>
          <p>{{ progressMessage }}</p>
        </div>
      </div>

      <!-- Configuration Form -->
      <form *ngIf="!isConfiguring" [formGroup]="configForm" (ngSubmit)="onSubmit()" class="config-form">
        
        <!-- Connection Details Section -->
        <div class="form-section">
          <div class="section-header">
            <h3>Azure VM Connection Details</h3>
          </div>
          
          <div class="form-row">
            <mat-form-field appearance="outline" class="form-field">
              <mat-label>VM IP Address *</mat-label>
              <input matInput formControlName="vm_ip" placeholder="e.g., 4.246.178.26" required>
              <mat-icon matSuffix>computer</mat-icon>
              <mat-error *ngIf="configForm.get('vm_ip')?.hasError('required')">
                VM IP address is required
              </mat-error>
              <mat-error *ngIf="configForm.get('vm_ip')?.hasError('pattern')">
                Please enter a valid IP address
              </mat-error>
            </mat-form-field>
          </div>

          <div class="form-row">
            <mat-form-field appearance="outline" class="form-field">
              <mat-label>Username</mat-label>
              <input matInput formControlName="username" placeholder="e.g., azureuser">
              <mat-icon matSuffix>person</mat-icon>
            </mat-form-field>
          </div>

          <div class="form-row">
            <mat-form-field appearance="outline" class="form-field password-field">
              <mat-label>Password *</mat-label>
              <input matInput type="password" formControlName="password" placeholder="Enter VM password" required>
              <mat-icon matSuffix>lock</mat-icon>
              <mat-error *ngIf="configForm.get('password')?.hasError('required')">
                Password is required
              </mat-error>
            </mat-form-field>
          </div>
        </div>

        <!-- Collapsible Info Section -->
        <div *ngIf="showInfo" class="form-section info-section">
          <div class="info-content">
            <p><strong>What happens next?</strong></p>
            <p>Once you click "Configure Server", the system will:</p>
            <ul>
              <li>Connect to your Azure VM using SSH</li>
              <li>Fetch the Kubernetes configuration (kubeconfig)</li>
              <li>Extract server address and port from the kubeconfig</li>
              <li>Update server addresses and connection details</li>
              <li>Save configuration files and update the system</li>
              <li>Test the connection to verify everything works</li>
            </ul>
            <p><strong>Note:</strong> The port number will be automatically extracted from the kubeconfig file - no need to specify it manually.</p>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="dialog-actions">
          <button type="button" mat-button (click)="onCancel()" [disabled]="isConfiguring">
            <mat-icon>cancel</mat-icon>
            Cancel
          </button>
          <button type="submit" mat-raised-button color="primary" [disabled]="!configForm.valid || isConfiguring">
            <mat-icon>cloud_done</mat-icon>
            Configure Server
          </button>
        </div>
      </form>

      <!-- Error Result Only (Success closes dialog) -->
      <div *ngIf="configurationResult && !configurationResult.success" class="result-container">
        <div class="result-header error">
          <mat-icon>error</mat-icon>
          <h3>Configuration Failed</h3>
        </div>
        
        <div class="result-details">
          <div class="error-details">
            <p class="error-message">{{ configurationResult.message }}</p>
            <div *ngIf="configurationResult.details" class="error-details-list">
              <h4>Details:</h4>
              <ul>
                <li *ngFor="let detail of configurationResult.details">{{ detail }}</li>
              </ul>
            </div>
          </div>
        </div>

        <div class="result-actions">
          <button mat-button (click)="retryConfiguration()">
            <mat-icon>refresh</mat-icon>
            Retry
          </button>
          <button mat-raised-button color="primary" (click)="onClose()">
            <mat-icon>done</mat-icon>
            Close
          </button>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .server-config-dialog {
      max-width: 800px;
      width: 100%;
      max-height: 90vh;
      overflow-y: auto;
    }

    .dialog-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      padding: 24px 24px 0 24px;
      border-bottom: 1px solid #e0e0e0;
      margin-bottom: 24px;
    }

    .header-content {
      display: flex;
      align-items: center;
      flex: 1;
    }

    .title-row {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .header-text h2 {
      margin: 0;
      color: #1976d2;
      font-weight: 500;
    }

    .info-button {
      color: #1976d2;
      width: 20px;
      height: 20px;
      min-width: 20px;
      min-height: 20px;
      padding: 0;
      border-radius: 50%;
      transition: background-color 0.2s ease;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .info-button:hover {
      background-color: rgba(25, 118, 210, 0.1);
    }

    .info-button mat-icon {
      font-size: 16px;
      width: 16px;
      height: 16px;
      line-height: 16px;
    }

    .header-subtitle {
      margin: 4px 0 0 0;
      color: #666;
      font-size: 14px;
    }

    .close-button {
      color: #666;
    }

    .progress-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 48px 24px;
      text-align: center;
    }

    .progress-text h3 {
      margin: 16px 0 8px 0;
      color: #1976d2;
    }

    .progress-text p {
      margin: 0;
      color: #666;
    }

    .config-form {
      padding: 0 24px 24px 24px;
    }

    .form-section {
      margin-bottom: 32px;
    }

    .section-header {
      display: flex;
      align-items: center;
      margin-bottom: 20px;
      padding-bottom: 8px;
      border-bottom: 2px solid #f0f0f0;
    }

    .section-header h3 {
      margin: 0;
      color: #333;
      font-weight: 500;
    }

    .form-row {
      display: flex;
      flex-direction: column;
      margin-bottom: 16px;
    }

    .form-field {
      width: 100%;
    }

    .password-field {
      position: relative;
    }

    .full-width {
      grid-column: 1 / -1;
    }

    .template-chips {
      margin-top: 16px;
    }

    .template-chip {
      margin-right: 8px;
      margin-bottom: 8px;
    }

    .info-section {
      background-color: #f8f9fa;
      border: 1px solid #e9ecef;
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 24px;
    }

    .info-section .info-content {
      margin: 0;
    }

    .info-section .info-content p {
      margin: 0 0 12px 0;
      color: #495057;
    }

    .info-section .info-content ul {
      margin: 0;
      padding-left: 20px;
    }

    .info-section .info-content li {
      margin-bottom: 6px;
      color: #495057;
    }

    .info-content {
      background-color: #f8f9fa;
      padding: 16px;
      border-radius: 8px;
      border-left: 4px solid #1976d2;
    }

    .info-content p {
      margin: 0 0 12px 0;
      font-weight: 500;
      color: #333;
    }

    .info-content ul {
      margin: 0;
      padding-left: 20px;
    }

    .info-content li {
      margin-bottom: 6px;
      color: #666;
      line-height: 1.4;
    }

    .dialog-actions {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
      margin-top: 32px;
      padding-top: 24px;
      border-top: 1px solid #e0e0e0;
    }

    .result-container {
      padding: 24px;
    }

    .result-header {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 24px;
      padding: 16px;
      border-radius: 8px;
    }

    .result-header.success {
      background-color: #e8f5e8;
      color: #2e7d32;
    }

    .result-header.error {
      background-color: #ffebee;
      color: #c62828;
    }

    .result-header mat-icon {
      font-size: 24px;
      width: 24px;
      height: 24px;
    }

    .result-header h3 {
      margin: 0;
      font-weight: 500;
    }

    .result-details {
      margin-bottom: 24px;
    }

    .detail-row {
      display: flex;
      margin-bottom: 12px;
      align-items: flex-start;
    }

    .detail-label {
      font-weight: 500;
      color: #666;
      min-width: 120px;
      margin-right: 16px;
    }

    .detail-value {
      color: #333;
      flex: 1;
    }

    .success-text {
      color: #2e7d32;
      display: flex;
      align-items: center;
      gap: 4px;
    }

    .nodes-output {
      background-color: #f5f5f5;
      padding: 8px;
      border-radius: 4px;
      font-family: 'Courier New', monospace;
      font-size: 12px;
      white-space: pre-wrap;
      margin: 0;
    }

    .error-message {
      color: #c62828;
      font-weight: 500;
      margin-bottom: 16px;
    }

    .error-details-list h4 {
      margin: 0 0 8px 0;
      color: #c62828;
    }

    .error-details-list ul {
      margin: 0;
      padding-left: 20px;
    }

    .error-details-list li {
      color: #c62828;
      margin-bottom: 4px;
    }

    .result-actions {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
    }

    @media (max-width: 768px) {
      .form-row {
        grid-template-columns: 1fr;
      }
      
      .dialog-actions {
        flex-direction: column;
      }
      
      .result-actions {
        flex-direction: column;
      }
    }
  `]
})
export class ServerConfigDialogComponent implements OnInit {
  configForm: FormGroup;
  isConfiguring = false;
  progressMessage = 'Initializing...';
  configurationResult: any = null;
  showInfo = false;

  constructor(
    private dialogRef: MatDialogRef<ServerConfigDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: ServerConfigData,
    private formBuilder: FormBuilder,
    private http: HttpClient,
    private snackBar: MatSnackBar
  ) {
    this.configForm = this.formBuilder.group({
      vm_ip: ['', [Validators.required, Validators.pattern(/^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/)]],
      username: ['azureuser'],
      password: ['', Validators.required]
    });
  }

  ngOnInit() {
    // Pre-fill form with data if provided
    if (this.data) {
      this.configForm.patchValue(this.data);
    }
  }

  applyTemplate(template: string) {
    // Templates are no longer needed since we only need basic connection details
    this.showSnackBar('Templates removed - only VM IP, username, and password are required', 'info');
  }

  toggleInfo() {
    this.showInfo = !this.showInfo;
  }



  onSubmit() {
    if (!this.configForm.valid) {
      this.showSnackBar('Please fill in all required fields', 'error');
      return;
    }

    this.isConfiguring = true;
    this.progressMessage = 'Connecting to Azure VM...';

    const configData = this.configForm.value;
    
    // Auto-generate server details based on VM IP
    const enhancedConfigData = {
      host: configData.vm_ip,  // Map vm_ip to host for backend
      username: configData.username,
      password: configData.password,
      name: `Azure VM Kubernetes (${configData.vm_ip})`,
      location: 'Azure VM',
      description: `Kubernetes cluster on Azure VM ${configData.vm_ip}`,
      configured_by: 'api'
    };

    this.http.post(ApiConfig.getServerConfigConfigureUrl(), enhancedConfigData)
      .subscribe({
        next: (response: any) => {
          this.isConfiguring = false;
          
          if (response.type === 'success') {
            // Success: Close dialog and show success message
            this.showSnackBar('Server configured successfully!', 'success');
            this.dialogRef.close({
              status: 'success',
              data: response.data,
              message: 'Server configured successfully!'
            });
          } else {
            // Error: Show error in dialog
            this.configurationResult = {
              success: false,
              message: response.message || 'Configuration failed',
              details: response.details || []
            };
            this.progressMessage = 'Configuration failed';
            this.showSnackBar(response.message || 'Configuration failed', 'error');
          }
        },
        error: (error) => {
          this.isConfiguring = false;
          this.configurationResult = {
            success: false,
            message: error.error?.message || 'Configuration failed',
            details: error.error?.details || []
          };
          this.progressMessage = 'Configuration failed';
          this.showSnackBar(error.error?.message || 'Configuration failed', 'error');
        }
      });
  }

  retryConfiguration() {
    this.configurationResult = null;
    this.onSubmit();
  }

  onCancel() {
    if (!this.isConfiguring) {
      this.dialogRef.close();
    }
  }

  onClose() {
    this.dialogRef.close(this.configurationResult);
  }

  private showSnackBar(message: string, type: 'success' | 'error' | 'info' = 'info') {
    this.snackBar.open(message, 'Close', {
      duration: 4000,
      horizontalPosition: 'center',
      verticalPosition: 'bottom',
      panelClass: type === 'error' ? ['error-snackbar'] : type === 'success' ? ['success-snackbar'] : []
    });
  }
} 