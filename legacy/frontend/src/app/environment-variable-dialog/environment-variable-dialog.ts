import { Component, EventEmitter, Inject, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-environment-variable-dialog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule
  ],
  template: `
    <h2 mat-dialog-title>Environment Variable</h2>
    <mat-dialog-content>
      <form #envForm="ngForm" class="env-form">
        <mat-form-field appearance="outline">
          <mat-label>Environment Variable</mat-label>
          <input matInput [(ngModel)]="environmentVariable" name="environmentVariable" required>
          <mat-hint>Enter the environment variable for the pod</mat-hint>
        </mat-form-field>
      </form>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button (click)="onCancel()">Cancel</button>
      <button mat-raised-button color="primary" 
              (click)="onSubmit()" 
              [disabled]="!envForm.form.valid || !environmentVariable">
        Set Environment Variable
      </button>
    </mat-dialog-actions>
  `,
  styles: [`
    .env-form {
      display: grid;
      grid-template-columns: 1fr;
      gap: 16px;
      padding: 16px 0;
      max-height: 60vh;
      overflow-y: auto;
    }
    mat-form-field {
      width: 100%;
    }
    mat-hint {
      font-size: 0.85rem;
      color: #666;
    }
    @media (max-width: 900px) {
      .env-form {
        padding: 8px 2px 4px 2px;
      }
    }
  `]
})
export class EnvironmentVariableDialogComponent {
  @Output() environmentVariableSet = new EventEmitter<string>();
  
  environmentVariable: string = '';

  constructor(
    private dialogRef: MatDialogRef<EnvironmentVariableDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: any
  ) {
    // Initialize with existing environment variable if provided
    if (data && data.environmentVariable) {
      this.environmentVariable = data.environmentVariable;
    }
  }

  onSubmit(): void {
    if (this.environmentVariable.trim()) {
      this.environmentVariableSet.emit(this.environmentVariable.trim());
      this.dialogRef.close(this.environmentVariable.trim());
    }
  }

  onCancel(): void {
    this.dialogRef.close();
  }
} 