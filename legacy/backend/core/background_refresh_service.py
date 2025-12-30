"""
Background Refresh Service
Automatically fetches live data from Kubernetes clusters and updates master.json
"""

import threading
import time
from datetime import datetime
from typing import Dict, List
import os
import json

class BackgroundRefreshService:
    """Background service for refreshing live data from Kubernetes clusters."""
    
    def __init__(self):
        self.running = False
        self.refresh_thread = None
        self.refresh_interval = 60  # Default 60 seconds
        self.auto_refresh_enabled = True
        
    def start(self):
        """Start the background refresh service."""
        if self.running:
            print("⚠️  Background refresh service is already running")
            return
        
        self.running = True
        self.refresh_thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self.refresh_thread.start()
        print("✅ Background refresh service started")
    
    def stop(self):
        """Stop the background refresh service."""
        self.running = False
        if self.refresh_thread:
            self.refresh_thread.join(timeout=5)
        print("🛑 Background refresh service stopped")
    
    def _refresh_loop(self):
        """Main refresh loop that runs in background."""
        while self.running:
            try:
                # Get current configuration
                self._load_refresh_config()
                
                if self.auto_refresh_enabled:
                    print(f"🔄 Background refresh: Fetching live data from Kubernetes clusters...")
                    self._refresh_all_servers()
                    print(f"✅ Background refresh completed at {datetime.now().isoformat()}")
                else:
                    print("⏸️  Background refresh disabled by configuration")
                
                # Wait for next refresh cycle
                time.sleep(self.refresh_interval)
                
            except Exception as e:
                print(f"❌ Background refresh error: {e}")
                time.sleep(30)  # Wait 30 seconds before retrying
    
    def _load_refresh_config(self):
        """Load refresh configuration from master.json."""
        try:
            config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'master.json')
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            refresh_config = config.get('config', {})
            self.auto_refresh_enabled = refresh_config.get('auto_refresh_enabled', True)
            
            # Get the minimum refresh interval from all servers
            servers = config.get('servers', [])
            if servers:
                min_interval = min(server.get('live_refresh_interval', 60) for server in servers)
                self.refresh_interval = min_interval
                print(f"🔧 Background refresh using minimum interval: {min_interval}s from {len(servers)} servers")
            else:
                self.refresh_interval = 60  # Default if no servers
                print("🔧 Background refresh using default interval: 60s (no servers configured)")
            
        except Exception as e:
            print(f"⚠️  Failed to load refresh config: {e}, using defaults")
            self.refresh_interval = 60
            self.auto_refresh_enabled = True
    
    def _refresh_all_servers(self):
        """Refresh live data for all configured servers."""
        try:
            from core.server_manager import server_manager
            from core.server_configuration_api import _fetch_and_update_live_data
            
            # Reload server manager to ensure fresh configuration
            server_manager.reload_config()
            
            # Get all configured servers
            config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'master.json')
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            servers = config.get('servers', [])
            successful_refreshes = 0
            
            for server in servers:
                server_id = server.get('id')
                if server_id:
                    try:
                        result = _fetch_and_update_live_data(server_id)
                        if result.get('type') == 'success':
                            successful_refreshes += 1
                            print(f"✅ Refreshed server: {server_id}")
                        else:
                            print(f"⚠️  Failed to refresh server {server_id}: {result.get('message')}")
                    except Exception as e:
                        print(f"❌ Error refreshing server {server_id}: {e}")
            
            # Update last refresh timestamp
            self._update_last_refresh()
            
            print(f"📊 Background refresh summary: {successful_refreshes}/{len(servers)} servers refreshed")
            
        except Exception as e:
            print(f"❌ Background refresh failed: {e}")
    
    def _update_last_refresh(self):
        """Update the last refresh timestamp in master.json."""
        try:
            config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'master.json')
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            if 'config' not in config:
                config['config'] = {}
            
            config['config']['last_live_refresh'] = datetime.now().isoformat()
            
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
                
        except Exception as e:
            print(f"⚠️  Failed to update last refresh timestamp: {e}")

# Global instance
background_refresh_service = BackgroundRefreshService() 