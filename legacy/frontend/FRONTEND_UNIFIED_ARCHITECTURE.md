# Frontend Unified Architecture - Resource Manager

## Overview

The frontend has been successfully updated to support the new **unified architecture** that replaces the old mode-based system with a server-based selection system.

## Key Changes

### 1. **Replaced Mode Selector with Server Selector**

#### **Old Mode-Based UI:**
- Mode dropdown with `demo`, `local-k8s`, `cloud-k8s`
- Mode-specific behavior and API calls
- Complex mode switching logic

#### **New Server-Based UI:**
- Server selector dropdown showing all available servers
- Server-specific information (name, status, type, location)
- Unified API calls with `server_id` parameter

### 2. **Updated Component Structure**

#### **App Component (`app.ts`)**
```typescript
// New properties
availableServers: any[] = [];        // All servers from master.json
selectedServer: any = null;          // Currently selected server
showServerSelector: boolean = false; // Server dropdown visibility

// New methods
isUnifiedMode(): boolean             // Always returns true
toggleServerSelector()               // Toggle server dropdown
selectServer(server: any)            // Select a server
```

#### **Updated API Calls**
```typescript
// Old: Mode-based API calls
fetchServers() // Fetched based on current mode

// New: Unified API calls
fetchServers() // Fetches all servers from /servers endpoint
deployPod(podData, serverId) // Uses server_id parameter
deletePod(pod) // Uses server_id parameter
```

### 3. **New UI Components**

#### **Server Selector Header**
```html
<!-- Server Selector -->
<div class="server-selector-container" (click)="toggleServerSelector()">
  <div class="server-selector-icon">
    <mat-icon>dns</mat-icon>
  </div>
  <div class="current-server-info" *ngIf="selectedServer">
    <span class="server-name">{{ selectedServer.server_name }}</span>
    <span class="server-status">{{ selectedServer.status }}</span>
  </div>
  <div class="no-server-selected" *ngIf="!selectedServer">
    <span>Select Server</span>
  </div>
</div>
```

#### **Server Dropdown**
```html
<div class="server-selector-dropdown" *ngIf="showServerSelector">
  <div class="server-selector-header">
    <h3>Select Server</h3>
    <button mat-icon-button (click)="toggleServerSelector()">
      <mat-icon>close</mat-icon>
    </button>
  </div>
  <div class="server-list">
    <div class="server-item" 
         *ngFor="let server of availableServers" 
         (click)="selectServer(server)">
      <div class="server-item-header">
        <span class="server-item-name">{{ server.server_name }}</span>
        <span class="server-item-status">{{ server.status }}</span>
      </div>
      <div class="server-item-details">
        <span class="server-type">{{ server.server_type }}</span>
        <span class="server-location">{{ server.metadata?.location }}</span>
      </div>
      <div class="server-item-pods">{{ server.pods.length }} pods</div>
    </div>
  </div>
</div>
```

### 4. **Updated API Integration**

#### **Server Data Structure**
```typescript
interface Server {
  server_id: string;           // Unique server identifier
  server_name: string;         // Display name
  server_type: string;         // 'kubernetes', 'mock', etc.
  status: string;              // 'Online', 'Offline', 'Error'
  metadata: {
    location: string;          // 'Azure East US', 'Local', etc.
    environment: string;       // 'production', 'development'
    description: string;       // Server description
  };
  pods: Pod[];                 // Array of pods on this server
  resources: {
    total: ResourceInfo;
    available: ResourceInfo;
  };
}
```

#### **API Endpoints**
```typescript
// GET /servers - Get all servers
fetchServers() {
  this.http.get<any[]>(ApiConfig.getServersUrl())
}

// POST /create - Create pod on specific server
deployPod(podData: any, serverId: string) {
  const payload = { ...podData, server_id: serverId };
  this.http.post(ApiConfig.getCreatePodUrl(), payload)
}

// POST /delete - Delete pod from specific server
deletePod(pod: any) {
  const payload = {
    server_id: this.selectedServer.server_id,
    PodName: pod.pod_id
  };
  this.http.post(ApiConfig.getDeletePodUrl(), payload)
}
```

### 5. **Removed Mode-Based Code**

#### **Removed Components:**
- `ModeSelectorComponent` import and usage
- Mode-specific polling and checking
- Mode configuration management
- Mode-based conditional rendering

#### **Removed Methods:**
- `onModeChanged()`
- `getCurrentMode()`
- `updateCurrentModeDisplay()`
- `isRealKubernetesMode()`
- `startModePolling()`
- `checkMode()`

### 6. **New CSS Styles**

#### **Server Selector Styles**
```css
.server-selector-container {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  cursor: pointer;
  min-width: 200px;
}

.server-selector-dropdown {
  position: absolute;
  top: 80px;
  right: 20px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  z-index: 1000;
  min-width: 300px;
}
```

## Benefits

### 1. **Simplified User Experience**
- **Single Interface**: One UI works for all servers
- **Clear Selection**: Easy to see and select different servers
- **Consistent Behavior**: Same actions work across all servers

### 2. **Better Information Display**
- **Server Details**: Shows server name, status, type, location
- **Pod Count**: Displays number of pods on each server
- **Status Indicators**: Visual status indicators for each server

### 3. **Improved Maintainability**
- **Unified Codebase**: Single code path for all servers
- **No Mode Logic**: Eliminated complex mode switching
- **Cleaner API**: Consistent API calls with server_id

### 4. **Enhanced Scalability**
- **Dynamic Server List**: Automatically shows all servers from master.json
- **Easy Addition**: New servers appear automatically
- **Flexible Display**: Adapts to any number of servers

## Usage Examples

### 1. **Selecting a Server**
```typescript
// User clicks server selector
toggleServerSelector() // Shows dropdown

// User clicks on a server
selectServer(server) {
  this.selectedServer = server;
  this.showServerSelector = false;
  this.servers = [server]; // Update display
}
```

### 2. **Creating a Pod**
```typescript
// Open dialog with server context
openAddPodDialog() {
  const dialogRef = this.dialog.open(AddPodDialogComponent, {
    data: {
      serverId: this.selectedServer.server_id,
      serverName: this.selectedServer.server_name,
      serverResources: this.selectedServer.resources
    }
  });
}

// Deploy to selected server
deployPod(podData, this.selectedServer.server_id)
```

### 3. **Deleting a Pod**
```typescript
deletePod(pod) {
  const payload = {
    server_id: this.selectedServer.server_id,
    PodName: pod.pod_id
  };
  this.http.post(ApiConfig.getDeletePodUrl(), payload)
}
```

## Migration Guide

### From Old Frontend
1. **Remove Mode Dependencies**: Delete mode selector component
2. **Update API Calls**: Add `server_id` to all requests
3. **Update UI**: Replace mode selector with server selector
4. **Update Data Flow**: Use server-based data instead of mode-based

### Testing the New Frontend
```bash
# Start the frontend
cd frontend
npm start

# Expected behavior:
# 1. Server selector shows in header
# 2. Click to see available servers
# 3. Select a server to manage its pods
# 4. All operations work on selected server
```

## Next Steps

### 1. **Enhanced Features**
- Server health monitoring
- Server-specific configurations
- Server comparison views
- Bulk operations across servers

### 2. **UI Improvements**
- Server status badges
- Resource utilization charts
- Server performance metrics
- Quick server switching

### 3. **User Experience**
- Server favorites
- Recent servers
- Server search/filter
- Server grouping

## Conclusion

The frontend has been successfully updated to support the unified architecture:

- ✅ **Eliminated mode complexity**
- ✅ **Added server-based selection**
- ✅ **Unified API integration**
- ✅ **Improved user experience**
- ✅ **Enhanced maintainability**

The Resource Manager frontend now provides a clean, scalable interface for managing multiple Kubernetes clusters through the unified architecture! 