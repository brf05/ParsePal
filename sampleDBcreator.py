import sqlite3
import os
import random
from datetime import datetime, timedelta

def make_sample_whatsapp_db(filename="sample_dbs/msgstore.db", message_count=1000):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    media_folder = os.path.join(os.path.dirname(filename), "media")
    os.makedirs(media_folder, exist_ok=True)

    # Place some sample images in media_folder before running this script (important)
    sample_images = [os.path.join(media_folder, f) for f in os.listdir(media_folder) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    if not sample_images:
        print(f"⚠️  No images found in {media_folder}. Add some .jpg or .png files for media messages.")
    
    if os.path.exists(filename):
        os.remove(filename)

    conn = sqlite3.connect(filename)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE messages (
            _id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_remote_jid TEXT,
            data TEXT,
            timestamp INTEGER,
            key_from_me INTEGER,
            media_name TEXT,
            media_mime_type TEXT,
            media_wa_type TEXT
        );
    """)

    contacts = [f"{random.randint(10000,99999)}@s.whatsapp.net" for _ in range(10)]

    base_time = datetime(2023, 1, 1)
    messages = []
    for i in range(message_count):
        contact = random.choice(contacts)
        text = random.choice([
            "Hello!", "How are you?", "What's up?", "See you soon.", "Good morning!",
            "Thanks!", "Okay", "I'll be there.", "Can't talk now", "Yes", "No", "Maybe",
            "Sure thing", "That's fine", "Haha", "Lol", "Nice!", "Alright", "On my way", "Great!"
        ])
        timestamp = int((base_time + timedelta(seconds=i * random.randint(30, 300))).timestamp() * 1000)
        key_from_me = random.randint(0, 1)  # 0 = received, 1 = sent

        # Randomly assign media to some messages
        if random.random() < 0.3:  # 30% chance to add media
            media_file = os.path.abspath(random.choice(sample_images))
            media_name = media_file
            media_mime_type = "image/jpeg" if media_name.lower().endswith('.jpg') or media_name.lower().endswith('.jpeg') else "image/png"
            media_wa_type = "image"
            messages.append((contact, text, timestamp, key_from_me, media_name, media_mime_type, media_wa_type))
        else:
            messages.append((contact, text, timestamp, key_from_me, None, None, None))

    cur.executemany("INSERT INTO messages (key_remote_jid, data, timestamp, key_from_me, media_name, media_mime_type, media_wa_type) VALUES (?, ?, ?, ?, ?, ?, ?)", messages)
    conn.commit()
    conn.close()

    print(f"✅ Created {message_count} fake WhatsApp messages with key_from_me in {filename}")

if __name__ == "__main__":
    make_sample_whatsapp_db()
