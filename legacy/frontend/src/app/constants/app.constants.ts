/**
 * Application constants and enums for Resource Manager frontend.
 * Centralized definition of all constants used throughout the application.
 */



export enum PodStatus {
  RUNNING = 'Running',
  PENDING = 'Pending',
  FAILED = 'Failed',
  TERMINATED = 'Terminated',
  UNKNOWN = 'Unknown'
}

export enum ResourceType {
  GPUS = 'gpus',
  RAM_GB = 'ram_gb',
  STORAGE_GB = 'storage_gb'
}

export enum ApiResponse {
  SUCCESS = 'success',
  ERROR = 'error',
  WARNING = 'warning'
}

export enum HttpStatus {
  OK = 200,
  CREATED = 201,
  BAD_REQUEST = 400,
  UNAUTHORIZED = 401,
  NOT_FOUND = 404,
  CONFLICT = 409,
  INTERNAL_SERVER_ERROR = 500
}

export class DefaultValues {
  // Default container images
  static readonly DEFAULT_IMAGE = 'nginx:latest';
  static readonly DEFAULT_IMAGE_DEV = 'nginx:latest';
  static readonly DEFAULT_IMAGE_PROD = 'nginx:latest';

  // Default resource values
  static readonly DEFAULT_CPU = 1;
  static readonly DEFAULT_MEMORY_GB = 1;
  static readonly DEFAULT_GPUS = 0;
  static readonly DEFAULT_STORAGE_GB = 1;

  // Default pod settings
  static readonly DEFAULT_OWNER = 'unknown';
  static readonly DEFAULT_REPLICAS = 1;
  static readonly DEFAULT_PORT = 80;
  static readonly DEFAULT_TARGET_PORT = 80;
}

export class ApiEndpoints {
  // API endpoint paths
  static readonly ROOT = '/';
  static readonly SERVERS = '/servers';
  static readonly CREATE_POD = '/create';
  static readonly DELETE_POD = '/delete';
  static readonly RESOURCE_VALIDATION = '/resource-validation';
  static readonly HEALTH_CHECK = '/health';
}

export class ContentTypes {
  // HTTP content types
  static readonly JSON = 'application/json';
  static readonly TEXT_HTML = 'text/html';
  static readonly TEXT_PLAIN = 'text/plain';
}

export class TimeFormats {
  // Time format constants
  static readonly ISO_FORMAT = 'YYYY-MM-DDTHH:mm:ssZ';
  static readonly DISPLAY_FORMAT = 'YYYY-MM-DD HH:mm:ss';
  static readonly LOG_FORMAT = 'YYYY-MM-DD HH:mm:ss';
}

export class ValidationRules {
  // Pod name rules
  static readonly POD_NAME_MIN_LENGTH = 1;
  static readonly POD_NAME_MAX_LENGTH = 63;
  static readonly POD_NAME_PATTERN = /^[a-z0-9]([a-z0-9-]*[a-z0-9])?$/;

  // Resource limits
  static readonly MAX_GPUS = 16;
  static readonly MAX_RAM_GB = 1024;
  static readonly MAX_STORAGE_GB = 10000;

  // Image URL patterns
  static readonly DOCKER_HUB_PATTERN = /^[a-zA-Z0-9][a-zA-Z0-9._-]*\/[a-zA-Z0-9][a-zA-Z0-9._-]*:[a-zA-Z0-9._-]+$/;
  static readonly FULL_URL_PATTERN = /^https?:\/\/[^\s\/$.?#].[^\s]*$/;
}

export class ErrorMessages {
  // Validation errors
  static readonly POD_NAME_REQUIRED = 'Pod name is required.';
  static readonly POD_NAME_LOWERCASE = 'Pod name must be lowercase.';
  static readonly POD_NAME_NO_UNDERSCORE = 'Pod name must not contain underscores.';
  static readonly RESOURCES_REQUIRED = 'Resources must be specified.';
  static readonly IMAGE_URL_REQUIRED = 'Image URL is required.';

  // Resource errors
  static readonly INSUFFICIENT_RESOURCES = 'Not enough {resource} available. Requested: {requested}, Available: {available}';
  static readonly RESOURCE_VALIDATION_ERROR = 'Invalid resource specification.';

  // API errors
  static readonly INVALID_JSON = 'Invalid JSON data';
  static readonly MISSING_FIELDS = 'Missing required field: {fields}';
  static readonly SERVER_NOT_FOUND = 'Server \'{serverId}\' not found.';
  static readonly POD_NOT_FOUND = 'Pod \'{podName}\' not found on any server.';

  // General errors
  static readonly SERVER_ERROR = 'Server error';
  static readonly UNKNOWN_ERROR = 'An unknown error occurred';
  static readonly NETWORK_ERROR = 'Network error occurred';
  static readonly TIMEOUT_ERROR = 'Request timeout';
}

export class SuccessMessages {
  // Standard success messages
  static readonly POD_CREATED = 'Pod created successfully';
  static readonly POD_DELETED = 'Pod deleted successfully';
  static readonly OPERATION_SUCCESS = 'Operation completed successfully';
  static readonly DATA_LOADED = 'Data loaded successfully';
  static readonly CONFIGURATION_SAVED = 'Configuration saved successfully';
}

export class UIConstants {
  // UI-specific constants
  static readonly DIALOG_WIDTH = '500px';
  static readonly DIALOG_HEIGHT = '600px';
  static readonly SNACKBAR_DURATION = 3000;
  static readonly DEBOUNCE_TIME = 300;
  static readonly MAX_RETRIES = 3;
  static readonly RETRY_DELAY = 1000;

  // Form validation
  static readonly MIN_POD_NAME_LENGTH = 1;
  static readonly MAX_POD_NAME_LENGTH = 63;
  static readonly MIN_RESOURCE_VALUE = 0;
  static readonly MAX_RESOURCE_VALUE = 1000;

  // Table settings
  static readonly PAGE_SIZE = 10;
  static readonly PAGE_SIZE_OPTIONS = [5, 10, 25, 50];
  static readonly SORT_DIRECTION_ASC = 'asc';
  static readonly SORT_DIRECTION_DESC = 'desc';
}



export class LocalStorageKeys {
  // Local storage keys
  static readonly USER_PREFERENCES = 'user_preferences';
  static readonly AUTH_TOKEN = 'auth_token';
  static readonly REFRESH_TOKEN = 'refresh_token';
  static readonly THEME = 'theme';
  static readonly LANGUAGE = 'language';
  static readonly LAST_VISITED = 'last_visited';
}

export class SessionStorageKeys {
  // Session storage keys
  static readonly CURRENT_SERVER = 'current_server';
  static readonly FILTER_STATE = 'filter_state';
  static readonly SORT_STATE = 'sort_state';
  static readonly PAGINATION_STATE = 'pagination_state';
}

export class EventTypes {
  // Custom event types
  static readonly POD_CREATED = 'podCreated';
  static readonly POD_DELETED = 'podDeleted';
  static readonly SERVER_SELECTED = 'serverSelected';
  static readonly FILTER_CHANGED = 'filterChanged';
  static readonly SORT_CHANGED = 'sortChanged';
  static readonly THEME_CHANGED = 'themeChanged';
  static readonly LANGUAGE_CHANGED = 'languageChanged';
}

export class AnimationDurations {
  // Animation duration constants
  static readonly FAST = 150;
  static readonly NORMAL = 300;
  static readonly SLOW = 500;
  static readonly VERY_SLOW = 1000;
}

export class Breakpoints {
  // Responsive breakpoints
  static readonly XS = 0;
  static readonly SM = 600;
  static readonly MD = 960;
  static readonly LG = 1280;
  static readonly XL = 1920;
} 