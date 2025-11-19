# Jellyfin Watch History Sync Tool

A Python tool to synchronize user watch history and user accounts from one Jellyfin server to another. Compatible with Jellyfin 10.11.x.

## ✨ Features

- **User Synchronization**: Automatically create missing users from source server on destination
  - Users are created without passwords (regardless of source password status)
  - Users must set their password on first login
- **Watch History Sync**: Transfer watched items, playback progress, and play dates
- **Flexible Sync Options**: Sync specific users or all users at once
- **Real-time Progress Tracking**: Shows total, completed, and remaining items during sync
- **Smart Detection**: Automatically detects common users and missing items
- **Error Handling**: Gracefully handles network errors and missing items

## 📋 Requirements

- Python 3.7 or higher
- Jellyfin 10.11.x servers
- API keys for both source and destination servers

## 🚀 Quick Start

### Installation

1. Clone this repository:
```bash
git clone https://github.com/RubyEyedReaper/WatchHero-V1-Sync.git
cd WatchHero-V1-Sync
```

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

3. Configure your servers in `config.ini`:
```ini
[Source]
server1UrlBase=https://your-source-server.com/
server1ApiKey=your-source-api-key

[destination]
server2UrlBase=https://your-destination-server.com/
server2ApiKey=your-destination-api-key
```

### Usage

Run the script:
```bash
python jellyfin_sync.py
```

The script will:
1. Connect to both servers
2. Check for missing users and offer to create them
3. List all common users
4. Prompt you to sync a specific user or all users
5. Display real-time progress (total, completed, remaining)
6. Show a summary when complete

## 📖 How It Works

### User Synchronization (Optional)

1. Detects users on source server that don't exist on destination
2. Displays list of missing users with their password status
3. Offers to create missing users (all created without passwords)
4. Shows progress during user creation

### Watch History Synchronization

1. **User Detection**: Identifies users that exist on both servers
2. **Watch History Retrieval**: Fetches all watched items from the source server
3. **Sync Process**: For each watched item:
   - Verifies the item exists on the destination server
   - Marks the item as played on the destination
   - Updates playback progress if available
   - Preserves play dates and play counts
4. **Progress Tracking**: Real-time status updates during sync

## 📝 Configuration

The `config.ini` file contains your server configuration:

```ini
[Source]
server1UrlBase=https://your-source-server.com/
server1ApiKey=your-source-api-key

[destination]
server2UrlBase=https://your-destination-server.com/
server2ApiKey=your-destination-api-key
```

### Getting API Keys

1. Log into your Jellyfin server as an administrator
2. Go to **Dashboard** → **API Keys**
3. Create a new API key with appropriate permissions
4. Copy the API key to your `config.ini` file

## ⚠️ Important Notes

- **User Passwords**: Users created from source will have **no password set**, even if they had a password on the source server. Users must set their password on first login to the destination server.
- **Item Matching**: Items are matched by Item ID. Items that don't exist on the destination server will be skipped.
- **Playback Progress**: The script preserves play dates and playback positions when available.
- **Duplicate Prevention**: Already synced items are automatically detected and skipped.

## 🔧 Troubleshooting

### Connection Errors

- Verify both servers are accessible from your network
- Check that API keys are correct and have proper permissions
- Ensure server URLs include the protocol (`https://` or `http://`)

### User Creation Fails

- Verify the API key has user management permissions
- Check that usernames don't contain invalid characters
- Ensure the destination server allows user creation

### Watch History Not Syncing

- Verify items exist on both servers (by Item ID)
- Check that the user has watched items on the source server
- Ensure API keys have read/write permissions for user data

## 📁 Project Structure

```
WatchHero-V1-Sync/
├── jellyfin_sync.py    # Main sync script
├── config.ini          # Server configuration
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is open source and available under the MIT License.

## 🙏 Acknowledgments

- Built for Jellyfin 10.11.x
- Uses the Jellyfin REST API
