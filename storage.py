import sqlite3

def init_db():
    conn = sqlite3.connect('server_data.db')
    cursor = conn.cursor()
    # server_data table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS server_data (
            guild_id TEXT PRIMARY KEY,
            role_id INTEGER,
            channel_id INTEGER
        )
    ''')
    # streamers table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS streamers (
            guild_id TEXT NOT NULL,
            streamer_name TEXT NOT NULL,
            PRIMARY KEY (guild_id, streamer_name)
        )
    ''')
    conn.commit()
    conn.close()

def get_server_data(guild_id):
    conn = sqlite3.connect('server_data.db')
    cursor = conn.cursor()
    cursor.execute('SELECT role_id, channel_id FROM server_data WHERE guild_id = ?', (guild_id,))
    row = cursor.fetchone()
    conn.close()
    return {"role_id": row[0], "channel_id": row[1]} if row else {"role_id": 0, "channel_id": 0}

def set_server_data(guild_id, role_id=None, channel_id=None):
    conn = sqlite3.connect('server_data.db')
    cursor = conn.cursor()

    # Retrieve existing data for the guild
    cursor.execute('SELECT role_id, channel_id FROM server_data WHERE guild_id = ?', (guild_id,))
    row = cursor.fetchone()

    # Determine new values, keeping existing ones if not provided
    new_role_id = role_id if role_id is not None else (row[0] if row else 0)
    new_channel_id = channel_id if channel_id is not None else (row[1] if row else 0)
    cursor.execute('''
        INSERT INTO server_data (guild_id, role_id, channel_id)
        VALUES (?, ?, ?)
        ON CONFLICT(guild_id) DO UPDATE SET
            role_id=excluded.role_id,
            channel_id=excluded.channel_id
    ''', (guild_id, new_role_id, new_channel_id))
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