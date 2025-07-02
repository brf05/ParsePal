import os

def find_sqlite_files(folder):
    db_files = []
    for root, _, files in os.walk(folder):
        for file in files:
            if file.endswith(".db"):
                db_files.append(os.path.join(root, file))
    return db_files
