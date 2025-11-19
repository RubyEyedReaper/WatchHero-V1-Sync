#!/usr/bin/env python3
"""
WatchHero v1
Jellyfin Watch History Sync Tool
Syncs user watch history from one Jellyfin server to another.
Compatible with Jellyfin 10.11.x
"""

import requests
import configparser
import sys
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class JellyfinClient:
    """Client for interacting with Jellyfin API"""
    
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'X-Emby-Token': api_key,
            'Content-Type': 'application/json'
        })
    
    def get_users(self) -> Dict[str, str]:
        """Get all users from the server. Returns dict of {username: user_id}"""
        try:
            url = f"{self.base_url}/Users"
            response = self.session.get(url)
            response.raise_for_status()
            users = response.json()
            return {user['Name']: user['Id'] for user in users}
        except requests.exceptions.RequestException as e:
            print(f"Error fetching users: {e}")
            return {}
    
    def get_users_detailed(self) -> List[Dict]:
        """Get all users with detailed information including password status"""
        try:
            url = f"{self.base_url}/Users"
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching user details: {e}")
            return []
    
    def create_user(self, username: str, has_password: bool = False) -> Optional[str]:
        """Create a new user on the server. Returns user_id if successful, None otherwise"""
        try:
            url = f"{self.base_url}/Users/New"
            data = {
                'Name': username,
                'HasPassword': has_password
            }
            response = self.session.post(url, json=data)
            response.raise_for_status()
            user_data = response.json()
            return user_data.get('Id')
        except requests.exceptions.RequestException as e:
            print(f"Error creating user {username}: {e}")
            return None
    
    def get_user_watched_items(self, user_id: str) -> List[Dict]:
        """Get all watched items for a user, including playback progress"""
        watched_items = []
        try:
            # Get played items
            url = f"{self.base_url}/Users/{user_id}/Items"
            params = {
                'Filters': 'IsPlayed',
                'Recursive': 'true',
                'Fields': 'UserData,MediaSources',
                'Limit': 200
            }
            
            start_index = 0
            while True:
                params['StartIndex'] = start_index
                response = self.session.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                items = data.get('Items', [])
                if not items:
                    break
                
                for item in items:
                    user_data = item.get('UserData', {})
                    if user_data.get('Played', False):
                        watched_items.append({
                            'Id': item['Id'],
                            'Name': item.get('Name', 'Unknown'),
                            'Type': item.get('Type', 'Unknown'),
                            'Played': True,
                            'PlayedDate': user_data.get('LastPlayedDate'),
                            'PlayCount': user_data.get('PlayCount', 0),
                            'PlaybackPositionTicks': user_data.get('PlaybackPositionTicks', 0),
                            'RuntimeTicks': item.get('RunTimeTicks', 0)
                        })
                
                start_index += len(items)
                if start_index >= data.get('TotalRecordCount', 0):
                    break
                    
        except requests.exceptions.RequestException as e:
            print(f"Error fetching watched items: {e}")
        
        return watched_items
    
    def mark_item_as_played(self, user_id: str, item_id: str, date_played: Optional[str] = None) -> bool:
        """Mark an item as played for a user"""
        try:
            url = f"{self.base_url}/Users/{user_id}/PlayedItems/{item_id}"
            params = {}
            if date_played:
                params['DatePlayed'] = date_played
            
            response = self.session.post(url, params=params)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error marking item as played: {e}")
            return False
    
    def update_playback_progress(self, user_id: str, item_id: str, position_ticks: int, 
                                 is_paused: bool = False) -> bool:
        """Update playback progress for an item"""
        try:
            url = f"{self.base_url}/Users/{user_id}/PlayingItems/{item_id}/Progress"
            data = {
                'PositionTicks': position_ticks,
                'IsPaused': is_paused
            }
            response = self.session.post(url, json=data)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error updating playback progress: {e}")
            return False
    
    def get_user_item_status(self, user_id: str, item_id: str) -> Optional[Dict]:
        """Get user data for a specific item"""
        try:
            url = f"{self.base_url}/Users/{user_id}/Items/{item_id}"
            params = {'Fields': 'UserData'}
            response = self.session.get(url, params=params)
            response.raise_for_status()
            item = response.json()
            return item.get('UserData')
        except requests.exceptions.RequestException as e:
            return None


class WatchHistorySyncer:
    """Main class for syncing watch history between Jellyfin servers"""
    
    def __init__(self, source_client: JellyfinClient, dest_client: JellyfinClient):
        self.source = source_client
        self.dest = dest_client
    
    def get_common_users(self) -> Dict[str, Tuple[str, str]]:
        """Get users that exist on both servers. Returns {username: (source_id, dest_id)}"""
        source_users = self.source.get_users()
        dest_users = self.dest.get_users()
        
        common = {}
        for username in source_users:
            if username in dest_users:
                common[username] = (source_users[username], dest_users[username])
        
        return common
    
    def sync_users(self) -> Dict:
        """Sync users from source to destination. Creates missing users without passwords."""
        print(f"\n{'='*60}")
        print("Syncing Users from Source to Destination")
        print(f"{'='*60}")
        
        # Get users from both servers
        print("Fetching users from source server...")
        source_users_detailed = self.source.get_users_detailed()
        source_users = {user['Name']: user for user in source_users_detailed}
        
        print("Fetching users from destination server...")
        dest_users = self.dest.get_users()
        
        # Find users that need to be created
        users_to_create = []
        for username, user_data in source_users.items():
            if username not in dest_users:
                has_password = user_data.get('HasPassword', False)
                users_to_create.append({
                    'Name': username,
                    'HasPassword': has_password
                })
        
        if not users_to_create:
            print("\nAll users from source already exist on destination.")
            return {'total': 0, 'created': 0, 'failed': 0}
        
        print(f"\nFound {len(users_to_create)} user(s) to create:")
        for user in users_to_create:
            password_status = "with password" if user['HasPassword'] else "without password"
            print(f"  - {user['Name']} ({password_status} on source, will be created without password)")
        
        total = len(users_to_create)
        created = 0
        failed = 0
        
        print(f"\nCreating users on destination server...")
        for idx, user in enumerate(users_to_create, 1):
            username = user['Name']
            # Always create without password, regardless of source password status
            user_id = self.dest.create_user(username, has_password=False)
            
            if user_id:
                created += 1
                remaining = total - idx
                print(f"[{idx}/{total}] ✓ Created user: {username} | Created: {created} | Remaining: {remaining}")
            else:
                failed += 1
                remaining = total - idx
                print(f"[{idx}/{total}] ✗ FAILED to create user: {username} | Created: {created} | Remaining: {remaining}")
        
        return {
            'total': total,
            'created': created,
            'failed': failed
        }
    
    def sync_user_watch_history(self, username: str, source_user_id: str, dest_user_id: str) -> Dict:
        """Sync watch history for a single user"""
        print(f"\n{'='*60}")
        print(f"Syncing watch history for user: {username}")
        print(f"{'='*60}")
        
        # Get watched items from source
        print("Fetching watched items from source server...")
        source_items = self.source.get_user_watched_items(source_user_id)
        
        if not source_items:
            print(f"No watched items found for {username} on source server.")
            return {'total': 0, 'completed': 0, 'skipped': 0, 'failed': 0}
        
        print(f"Found {len(source_items)} watched items on source server.")
        
        # Get existing watched items from destination
        print("Fetching existing watched items from destination server...")
        dest_items = self.dest.get_user_watched_items(dest_user_id)
        dest_item_ids = {item['Id'] for item in dest_items}
        
        # Filter items that need to be synced
        items_to_sync = [item for item in source_items if item['Id'] not in dest_item_ids]
        
        if not items_to_sync:
            print(f"All items already synced for {username}.")
            return {'total': len(source_items), 'completed': 0, 'skipped': len(source_items), 'failed': 0}
        
        print(f"Syncing {len(items_to_sync)} new items...")
        
        total = len(items_to_sync)
        completed = 0
        skipped = 0
        failed = 0
        
        for idx, item in enumerate(items_to_sync, 1):
            item_name = item['Name']
            item_id = item['Id']
            
            # Check if item exists on destination server
            dest_item_status = self.dest.get_user_item_status(dest_user_id, item_id)
            if dest_item_status is None:
                print(f"[{idx}/{total}] SKIPPED: {item_name} (item not found on destination)")
                skipped += 1
                continue
            
            # Mark as played
            success = self.dest.mark_item_as_played(
                dest_user_id, 
                item_id, 
                item.get('PlayedDate')
            )
            
            if success:
                # Update playback progress if available
                position_ticks = item.get('PlaybackPositionTicks', 0)
                if position_ticks > 0:
                    self.dest.update_playback_progress(
                        dest_user_id, 
                        item_id, 
                        position_ticks,
                        is_paused=True
                    )
                
                completed += 1
                remaining = total - idx
                print(f"[{idx}/{total}] ✓ {item_name} | Completed: {completed} | Remaining: {remaining}")
            else:
                failed += 1
                remaining = total - idx
                print(f"[{idx}/{total}] ✗ FAILED: {item_name} | Completed: {completed} | Remaining: {remaining}")
        
        return {
            'total': total,
            'completed': completed,
            'skipped': skipped,
            'failed': failed
        }
    
    def sync_all_users(self, users: Dict[str, Tuple[str, str]]) -> None:
        """Sync watch history for all users"""
        total_users = len(users)
        print(f"\nSyncing watch history for {total_users} users...\n")
        
        overall_stats = {'total': 0, 'completed': 0, 'skipped': 0, 'failed': 0}
        
        for idx, (username, (source_id, dest_id)) in enumerate(users.items(), 1):
            print(f"\n[{idx}/{total_users}] Processing user: {username}")
            stats = self.sync_user_watch_history(username, source_id, dest_id)
            
            overall_stats['total'] += stats['total']
            overall_stats['completed'] += stats['completed']
            overall_stats['skipped'] += stats['skipped']
            overall_stats['failed'] += stats['failed']
        
        # Print summary
        print(f"\n{'='*60}")
        print("SYNC SUMMARY")
        print(f"{'='*60}")
        print(f"Total items processed: {overall_stats['total']}")
        print(f"Successfully synced: {overall_stats['completed']}")
        print(f"Skipped (not found): {overall_stats['skipped']}")
        print(f"Failed: {overall_stats['failed']}")
        print(f"{'='*60}\n")


def load_config(config_file: str = 'config.ini') -> Optional[Tuple[str, str, str, str]]:
    """Load configuration from config file"""
    try:
        config = configparser.ConfigParser()
        config.read(config_file)
        
        source_url = config.get('Source', 'server1UrlBase', fallback=None)
        source_key = config.get('Source', 'server1ApiKey', fallback=None)
        dest_url = config.get('destination', 'server2UrlBase', fallback=None)
        dest_key = config.get('destination', 'server2ApiKey', fallback=None)
        
        if not all([source_url, source_key, dest_url, dest_key]):
            print("Error: Missing required configuration values in config.ini")
            return None
        
        return source_url, source_key, dest_url, dest_key
    except Exception as e:
        print(f"Error loading config: {e}")
        return None


def main():
    """Main function"""
    print("="*60)
    print("Jellyfin Watch History Sync Tool")
    print("="*60)
    
    # Load configuration
    config = load_config()
    if not config:
        sys.exit(1)
    
    source_url, source_key, dest_url, dest_key = config
    
    # Initialize clients
    print("\nConnecting to servers...")
    source_client = JellyfinClient(source_url, source_key)
    dest_client = JellyfinClient(dest_url, dest_key)
    
    # Initialize syncer
    syncer = WatchHistorySyncer(source_client, dest_client)
    
    # Check for users to sync
    print("Checking existing users on both servers...")
    source_users = source_client.get_users()
    dest_users = dest_client.get_users()
    
    missing_users = [user for user in source_users.keys() if user not in dest_users.keys()]
    
    if missing_users:
        print(f"\nFound {len(missing_users)} user(s) on source that don't exist on destination:")
        for username in missing_users:
            print(f"  - {username}")
        
        print("\n" + "="*60)
        print("User Sync Options:")
        print("  1. Sync users first (create missing users)")
        print("  2. Skip user sync and proceed to watch history")
        print("="*60)
        
        while True:
            user_sync_choice = input("\nEnter your choice (1 or 2): ").strip()
            
            if user_sync_choice == '1':
                # Sync users
                user_stats = syncer.sync_users()
                print(f"\n{'='*60}")
                print("USER SYNC SUMMARY")
                print(f"{'='*60}")
                print(f"Total users to create: {user_stats['total']}")
                print(f"Successfully created: {user_stats['created']}")
                print(f"Failed: {user_stats['failed']}")
                print(f"{'='*60}\n")
                
                if user_stats['failed'] > 0:
                    print("Warning: Some users failed to create. Watch history sync may be incomplete.")
                
                # Refresh user lists after creating users
                dest_users = dest_client.get_users()
                break
            elif user_sync_choice == '2':
                print("Skipping user sync...")
                break
            else:
                print("Invalid choice. Please enter 1 or 2.")
    
    # Get common users for watch history sync
    common_users = syncer.get_common_users()
    
    if not common_users:
        print("\nNo common users found between source and destination servers.")
        print("Cannot sync watch history without common users.")
        sys.exit(1)
    
    print(f"\nFound {len(common_users)} common user(s) for watch history sync:")
    for idx, username in enumerate(common_users.keys(), 1):
        print(f"  {idx}. {username}")
    
    # Ask user for watch history sync preference
    print("\n" + "="*60)
    print("Watch History Sync Options:")
    print("  1. Sync specific user")
    print("  2. Sync all users")
    print("="*60)
    
    while True:
        choice = input("\nEnter your choice (1 or 2): ").strip()
        
        if choice == '1':
            # Sync specific user
            print("\nAvailable users:")
            user_list = list(common_users.keys())
            for idx, username in enumerate(user_list, 1):
                print(f"  {idx}. {username}")
            
            while True:
                try:
                    user_choice = input("\nEnter user number to sync: ").strip()
                    user_idx = int(user_choice) - 1
                    if 0 <= user_idx < len(user_list):
                        selected_user = user_list[user_idx]
                        source_id, dest_id = common_users[selected_user]
                        stats = syncer.sync_user_watch_history(selected_user, source_id, dest_id)
                        
                        print(f"\n{'='*60}")
                        print("SYNC SUMMARY")
                        print(f"{'='*60}")
                        print(f"Total items: {stats['total']}")
                        print(f"Successfully synced: {stats['completed']}")
                        print(f"Skipped: {stats['skipped']}")
                        print(f"Failed: {stats['failed']}")
                        print(f"{'='*60}\n")
                        break
                    else:
                        print("Invalid user number. Please try again.")
                except ValueError:
                    print("Please enter a valid number.")
            break
        
        elif choice == '2':
            # Sync all users
            syncer.sync_all_users(common_users)
            break
        
        else:
            print("Invalid choice. Please enter 1 or 2.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSync interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

