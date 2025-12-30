# API Configuration Guide

## Overview

The Resource Manager frontend now uses a centralized API configuration system that makes it easy to change backend URLs and endpoints without modifying multiple files.

## Configuration Files

### 1. Environment Files

#### Development (`src/environments/environment.ts`)
```typescript
export const environment = {
  production: false,
  api: {
    host: '127.0.0.1',
    port: '5005',
    protocol: 'http'
  }
};
```

#### Production (`src/environments/environment.prod.ts`)
```typescript
export const environment = {
  production: true,
  api: {
    host: 'your-production-host.com',
    port: '443',
    protocol: 'https'
  }
};
```

### 2. API Configuration (`src/app/config/api.config.ts`)

This file contains all the centralized API logic and endpoint definitions.

## How to Change API Settings

### Option 1: Change Environment File (Recommended)

1. **For Development**: Edit `src/environments/environment.ts`
2. **For Production**: Edit `src/environments/environment.prod.ts`

Example - Change port from 5005 to 8080:
```typescript
export const environment = {
  production: false,
  api: {
    host: '127.0.0.1',
    port: '8080',  // Changed from '5005'
    protocol: 'http'
  }
};
```

### Option 2: Runtime Configuration

You can also change settings at runtime:

```typescript
import { ApiConfig } from './config/api.config';

// Change port
ApiConfig.setPort('8080');

// Change host
ApiConfig.setHost('localhost');
```

## Available Endpoints

All endpoints are automatically generated from the base URL:

- **Health Check**: `/health`
- **Detailed Health**: `/health/detailed`
- **Cluster Status**: `/cluster-status`
- **Consistency Check**: `/consistency-check`
- **Servers**: `/servers`
- **Create Pod**: `/create`
- **Delete Pod**: `/delete`
- **Update Pod**: `/update`

## Benefits

### ✅ **Single Source of Truth**
- All API URLs are generated from one base configuration
- No more hard-coded URLs scattered throughout the code

### ✅ **Environment-Aware**
- Different settings for development and production
- Easy to switch between environments

### ✅ **Type Safe**
- TypeScript ensures correct URL generation
- Compile-time validation of endpoints

### ✅ **Maintainable**
- Change one file to update all API calls
- Clear separation of concerns

### ✅ **Extensible**
- Easy to add new endpoints
- Simple to modify URL generation logic

## Usage Examples

### In Components
```typescript
import { ApiConfig } from './config/api.config';

// Get full URL for an endpoint
const healthUrl = ApiConfig.getHealthUrl();
const serversUrl = ApiConfig.getServersUrl();

// Check environment
if (ApiConfig.isDevelopment()) {
  console.log('Running in development mode');
}
```

### Configuration Validation
```typescript
// Logs current configuration to console
ApiConfig.validateConfig();
```

## Migration from Hard-coded URLs

### Before (Hard-coded)
```typescript
this.http.get('http://127.0.0.1:5005/health')
this.http.post('http://127.0.0.1:5005/create', data)
```

### After (Centralized)
```typescript
this.http.get(ApiConfig.getHealthUrl())
this.http.post(ApiConfig.getCreatePodUrl(), data)
```

## Troubleshooting

### Port Already in Use
If you get "Address already in use" error:

1. **Check what's using the port**:
   ```bash
   lsof -i :5005
   ```

2. **Change the port** in environment file:
   ```typescript
   port: '8080'  // Use different port
   ```

3. **Restart the frontend**:
   ```bash
   npm start
   ```

### Configuration Not Loading
1. **Check environment file** exists and is correct
2. **Verify imports** in `api.config.ts`
3. **Check console** for configuration validation output

## Best Practices

1. **Always use environment files** for configuration
2. **Never hard-code URLs** in components
3. **Use TypeScript** for type safety
4. **Validate configuration** on startup
5. **Document changes** in environment files 