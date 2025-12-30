/**
 * Environment configuration for development
 */
export const environment = {
  production: false,
  api: {
    host: '127.0.0.1',
    port: 5005,  // Backend is running on port 5005 (avoiding macOS AirPlay conflict)
    protocol: 'http'
  }
}; 