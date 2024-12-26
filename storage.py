import sqlite3

def init_db():
    conn = sqlite3.connect('server_data.db')
    cursor = conn.cursor()
    
    # Create server_data table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS server_data (
            guild_id TEXT PRIMARY KEY,
            role_id INTEGER,
            channel_id INTEGER,
            log_channel_id INTEGER,
            youtube_channel_id INTEGER,
            youtube_role_id INTEGER,
            youtube_channel TEXT
        )
    ''')
    
    # Create streamers table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS streamers (
            guild_id TEXT,
            streamer_name TEXT,
            PRIMARY KEY (guild_id, streamer_name)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized successfully.")

def migrate_db():
    conn = sqlite3.connect('server_data.db')
    cursor = conn.cursor()

    # Check if youtube_channel_id column exists
    cursor.execute("PRAGMA table_info(server_data)")
    columns = [column[1] for column in cursor.fetchall()]

    if 'youtube_channel_id' not in columns:
        cursor.execute('ALTER TABLE server_data ADD COLUMN youtube_channel_id INTEGER')
    if 'youtube_role_id' not in columns:
        cursor.execute('ALTER TABLE server_data ADD COLUMN youtube_role_id INTEGER')
    if 'youtube_channel' not in columns:
        cursor.execute('ALTER TABLE server_data ADD COLUMN youtube_channel TEXT')

    conn.commit()
    conn.close()
    print("Database migration completed successfully.")

def get_server_data(guild_id):
    conn = sqlite3.connect('server_data.db')
    cursor = conn.cursor()
    cursor.execute('SELECT role_id, channel_id, log_channel_id, youtube_channel_id, youtube_role_id, youtube_channel FROM server_data WHERE guild_id = ?', (guild_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {
            'role_id': result[0],
            'channel_id': result[1],
            'log_channel_id': result[2],
            'youtube_channel_id': result[3],
            'youtube_role_id': result[4],
            'youtube_channel': result[5]
        }
    return None

def set_server_data(guild_id, **kwargs):
    conn = sqlite3.connect('server_data.db')
    cursor = conn.cursor()
    
    # Check if the guild_id already exists
    cursor.execute('SELECT 1 FROM server_data WHERE guild_id = ?', (guild_id,))
    exists = cursor.fetchone()
    
    if exists:
        # Update existing record
        set_clause = ', '.join([f'{k} = ?' for k in kwargs.keys()])
        query = f'UPDATE server_data SET {set_clause} WHERE guild_id = ?'
        cursor.execute(query, list(kwargs.values()) + [guild_id])
    else:
        # Insert new record
        columns = ['guild_id'] + list(kwargs.keys())
        placeholders = '?' * (len(columns))
        query = f'INSERT INTO server_data ({", ".join(columns)}) VALUES ({", ".join(placeholders)})'
        cursor.execute(query, [guild_id] + list(kwargs.values()))
    
    conn.commit()
    conn.close()

def add_streamer(guild_id, streamer_name):
    conn = sqlite3.connect('server_data.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO streamers (guild_id, streamer_name)
        VALUES (?, ?)
        ON CONFLICT(guild_id, streamer_name) DO NOTHING
    ''', (guild_id, streamer_name))
    conn.commit()
    conn.close()

def remove_streamer(guild_id, streamer_name):
    conn = sqlite3.connect('server_data.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM streamers WHERE guild_id = ? AND streamer_name = ?', (guild_id, streamer_name))
    conn.commit()
    conn.close()

def get_streamers(guild_id):
    conn = sqlite3.connect('server_data.db')
    cursor = conn.cursor()
    cursor.execute('SELECT streamer_name FROM streamers WHERE guild_id = ?', (guild_id,))
    streamers = [row[0] for row in cursor.fetchall()]
    conn.close()
    return streamers

def get_all_guild_ids():
    """Retrieve all unique guild IDs from the server_data table."""
    conn = sqlite3.connect('server_data.db')
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT guild_id FROM server_data')
    guild_ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    return guild_ids

def get_youtube_settings(guild_id):
    conn = sqlite3.connect('server_data.db')
    cursor = conn.cursor()
    cursor.execute('SELECT youtube_channel_id, youtube_role_id, youtube_channel FROM server_data WHERE guild_id = ?', (guild_id,))
    result = cursor.fetchone()
    conn.close()
    return result if result else (None, None, None)

def set_youtube_settings(guild_id, youtube_channel_id, youtube_role_id, youtube_channel):
    set_server_data(guild_id, youtube_channel_id=youtube_channel_id, youtube_role_id=youtube_role_id, youtube_channel=youtube_channel)
    
def get_youtubers(guild_id):
    conn = sqlite3.connect('server_data.db')
    cursor = conn.cursor()
    cursor.execute('SELECT youtube_channel FROM server_data WHERE guild_id = ?', (guild_id,))
    result = cursor.fetchone()
    conn.close()
    if result and result[0]:
        return result[0].split(',')
    return []

def add_youtuber(guild_id, channel_name):
    conn = sqlite3.connect('server_data.db')
    cursor = conn.cursor()
    
    # Get current YouTube channels
    cursor.execute('SELECT youtube_channel FROM server_data WHERE guild_id = ?', (guild_id,))
    result = cursor.fetchone()
    
    if result and result[0]:
        channels = result[0].split(',')
        if channel_name not in channels:
            channels.append(channel_name)
            new_channels = ','.join(channels)
    else:
        new_channels = channel_name
    
    # Update the YouTube channels
    cursor.execute('UPDATE server_data SET youtube_channel = ? WHERE guild_id = ?', (new_channels, guild_id))
    
    # If no rows were updated, insert a new row
    if cursor.rowcount == 0:
        cursor.execute('INSERT INTO server_data (guild_id, youtube_channel) VALUES (?, ?)', (guild_id, new_channels))
    
    conn.commit()
    conn.close()

def remove_youtuber(guild_id, channel_name):
    conn = sqlite3.connect('server_data.db')
    cursor = conn.cursor()
    
    # Get current YouTube channels
    cursor.execute('SELECT youtube_channel FROM server_data WHERE guild_id = ?', (guild_id,))
    result = cursor.fetchone()
    
    if result and result[0]:
        channels = result[0].split(',')
        if channel_name in channels:
            channels.remove(channel_name)
            new_channels = ','.join(channels) if channels else None
            
            # Update the YouTube channels
            cursor.execute('UPDATE server_data SET youtube_channel = ? WHERE guild_id = ?', (new_channels, guild_id))
    
    conn.commit()
    conn.close()
    
def get_all_streamers(guild_id):
    twitch_streamers = get_streamers(guild_id)
    youtube_channels = get_youtubers(guild_id)
    return twitch_streamers + youtube_channels

def setup_database():
    init_db()
    migrate_db()