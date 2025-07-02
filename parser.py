import sqlite3
import pandas as pd
from datetime import datetime

def parse_db(db_path, app_name):
    if app_name.lower() != "whatsapp":
        raise NotImplementedError("Currently only WhatsApp is supported.")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get columns of messages table
        cursor.execute("PRAGMA table_info(messages);")
        table_info = cursor.fetchall()
        available_cols = [col[1] for col in table_info]

        # Columns to fetch if they exist
        desired_cols = [
            "key_remote_jid",
            "data",
            "timestamp",
            "media_name",
            "media_url",
            "media_mime_type",
            "media_wa_type",
            "key_from_me"
        ]

        selected_cols = [col for col in desired_cols if col in available_cols]

        # Build WHERE clause for messages with text or media
        where_clauses = []
        if "data" in available_cols:
            where_clauses.append("data IS NOT NULL")
        if "media_name" in available_cols:
            where_clauses.append("media_name IS NOT NULL")
        where_clause = " OR ".join(where_clauses) if where_clauses else "1=1"

        query = f"SELECT {', '.join(selected_cols)} FROM messages WHERE {where_clause} ORDER BY timestamp ASC"
        cursor.execute(query)
        rows = cursor.fetchall()

        results = []
        for row in rows:
            row_dict = dict(zip(selected_cols, row))

            timestamp = row_dict.get("timestamp")
            dt = None
            if timestamp is not None:
                try:
                    # WhatsApp stores timestamp in ms since epoch
                    if isinstance(timestamp, (int, float)):
                        if timestamp > 1e12:
                            dt = datetime.utcfromtimestamp(timestamp / 1000)
                        elif timestamp > 1e9:
                            dt = datetime.utcfromtimestamp(timestamp)
                except Exception:
                    dt = None

            media_path = row_dict.get("media_name") or row_dict.get("media_url")

            direction = None
            if "key_from_me" in row_dict:
                direction = "Sent" if row_dict["key_from_me"] == 1 else "Received"

            results.append({
                "Contact": row_dict.get("key_remote_jid"),
                "Message": row_dict.get("data"),
                "timestamp": dt,
                "media_path": media_path,
                "media_mime": row_dict.get("media_mime_type"),
                "media_type": row_dict.get("media_wa_type"),
                "Direction": direction
            })

        df = pd.DataFrame(results)
        return df

    except Exception as e:
        raise RuntimeError(f"Error parsing DB: {e}")

    finally:
        if 'conn' in locals():
            conn.close()
