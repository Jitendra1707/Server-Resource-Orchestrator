/**
 * API Configuration
 * Centralized configuration for all backend API endpoints and URLs
 */

import { environment } from '../../environments/environment';

export class ApiConfig {
  // Base URL configuration
  private static readonly DEFAULT_HOST = '127.0.0.1';
  private static readonly DEFAULT_PORT = '5005';
  private static readonly DEFAULT_PROTOCOL = 'http';
  

  
  // Get base URL from environment or use defaults
  private static getBaseUrl(): string {
    const host = environment.api?.host || this.DEFAULT_HOST;
    const port = environment.api?.port || this.DEFAULT_PORT;
    const protocol = environment.api?.protocol || this.DEFAULT_PROTOCOL;
    
    return `${protocol}://${host}:${port}`;
  }
  
  // Public base URL getter
  static get BASE_URL(): string {
    return this.getBaseUrl();
  }
  
  // API Endpoints
  static readonly ENDPOINTS = {
    // Health and monitoring endpoints
    HEALTH: '/health',
    HEALTH_DETAILED: '/health/detailed',

    RESOURCE_VALIDATION: '/resource-validation',
    
    // Resource management endpoints
    SERVERS: '/servers',
    CREATE_POD: '/create',
    DELETE_POD: '/delete',
    
    // Server configuration endpoints
    SERVER_CONFIG: '/api/server-config',
    SERVER_CONFIG_CONFIGURE: '/api/server-config/configure',
    SERVER_CONFIG_SERVERS: '/api/server-config/servers',
    SERVER_CONFIG_TEST: '/api/server-config/test',
    SERVER_CONFIG_DECONFIGURE: '/api/server-config/deconfigure',
    SERVER_CONFIG_RECONNECT: '/api/server-config/reconnect',
    SERVER_CONFIG_HEALTH: '/api/server-config/health',
    SERVER_CONFIG_REFRESH_CONFIG: '/api/server-config/config/refresh',
    
    // Root endpoint
    ROOT: '/'
  } as const;
  
  // Full URL getters
  static getHealthUrl(): string {
    return `${this.BASE_URL}${this.ENDPOINTS.HEALTH}`;
  }
  
  static getHealthDetailedUrl(): string {
    return `${this.BASE_URL}${this.ENDPOINTS.HEALTH_DETAILED}`;
  }
  

  
  static getResourceValidationUrl(): string {
    return `${this.BASE_URL}${this.ENDPOINTS.RESOURCE_VALIDATION}`;
  }
  
  static getServersUrl(): string {
    return `${this.BASE_URL}${this.ENDPOINTS.SERVERS}`;
  }
  
  static getCreatePodUrl(): string {
    return `${this.BASE_URL}${this.ENDPOINTS.CREATE_POD}`;
  }
  
  static getDeletePodUrl(): string {
    return `${this.BASE_URL}${this.ENDPOINTS.DELETE_POD}`;
  }
  

  
  // Server configuration URL getters
  static getServerConfigUrl(): string {
    return `${this.BASE_URL}${this.ENDPOINTS.SERVER_CONFIG}`;
  }
  
  static getServerConfigConfigureUrl(): string {
    return `${this.BASE_URL}${this.ENDPOINTS.SERVER_CONFIG_CONFIGURE}`;
  }
  
  static getServerConfigServersUrl(): string {
    return `${this.BASE_URL}${this.ENDPOINTS.SERVER_CONFIG_SERVERS}`;
  }
  
  static getServerConfigTestUrl(serverId: string): string {
    return `${this.BASE_URL}${this.ENDPOINTS.SERVER_CONFIG_TEST}/${serverId}`;
  }
  
  static getServerConfigDeconfigureUrl(serverId: string): string {
    return `${this.BASE_URL}${this.ENDPOINTS.SERVER_CONFIG_DECONFIGURE}/${serverId}`;
  }
  
  static getServerConfigHealthUrl(): string {
    return `${this.BASE_URL}${this.ENDPOINTS.SERVER_CONFIG_HEALTH}`;
  }
  
  static getServerConfigReconnectUrl(): string {
    return `${this.BASE_URL}${this.ENDPOINTS.SERVER_CONFIG_RECONNECT}`;
  }
  
  static getServerConfigRefreshConfigUrl(): string {
    return `${this.BASE_URL}${this.ENDPOINTS.SERVER_CONFIG_REFRESH_CONFIG}`;
  }
  
  static getRootUrl(): string {
    return `${this.BASE_URL}${this.ENDPOINTS.ROOT}`;
  }
  

  
  // Configuration override methods for runtime changes
  static setPort(port: string): void {
    (this as any).DEFAULT_PORT = port;
  }
  
  static setHost(host: string): void {
    (this as any).DEFAULT_HOST = host;
  }
  
  // Configuration validation
  static validateConfig(): void {
    console.log(`🔧 API Configuration:`);
    console.log(`   Base URL: ${this.BASE_URL}`);
    console.log(`   Health Check: ${this.getHealthUrl()}`);
    console.log(`   Servers: ${this.getServersUrl()}`);
  }
} 