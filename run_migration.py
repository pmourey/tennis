"""
Script de migration manuelle :
- Marque la migration de base comme appliquée dans alembic_version
- Ajoute les colonnes plays_single, plays_double, is_substitute à player_matchday_availability
- Crée la table team_matchday_joker si elle n'existe pas
- Ajoute les colonnes plays_single, plays_double à team_matchday_joker
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'tennis.sqlite3')
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# ── 1. alembic_version ────────────────────────────────────────────────────────
cur.execute("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL, CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))")
cur.execute("DELETE FROM alembic_version")
cur.execute("INSERT INTO alembic_version (version_num) VALUES ('b2c3d4e5f6a7')")
print("alembic_version -> b2c3d4e5f6a7")

# ── 2. Colonnes player_matchday_availability ───────────────────────────────────
existing = {row[1] for row in cur.execute("PRAGMA table_info(player_matchday_availability)").fetchall()}
print(f"player_matchday_availability colonnes existantes : {existing}")
for col, ddl in [
    ('plays_single',  "INTEGER NOT NULL DEFAULT 0"),
    ('plays_double',  "INTEGER NOT NULL DEFAULT 0"),
    ('is_substitute', "INTEGER NOT NULL DEFAULT 0"),
]:
    if col not in existing:
        cur.execute(f"ALTER TABLE player_matchday_availability ADD COLUMN {col} {ddl}")
        print(f"  + Colonne ajoutée : {col}")
    else:
        print(f"  = Déjà présente   : {col}")

# ── 3. Table team_matchday_joker ───────────────────────────────────────────────
cur.execute("""
CREATE TABLE IF NOT EXISTS team_matchday_joker (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id     INTEGER NOT NULL REFERENCES team(id) ON DELETE CASCADE,
    matchday_id INTEGER NOT NULL REFERENCES matchday(id) ON DELETE CASCADE,
    player_id   INTEGER REFERENCES player(id) ON DELETE SET NULL,
    plays_single INTEGER NOT NULL DEFAULT 0,
    plays_double INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT uq_team_matchday_joker UNIQUE (team_id, matchday_id)
)
""")
print("table team_matchday_joker : créée ou déjà existante")

# ── 4. Colonnes plays_single / plays_double dans team_matchday_joker ──────────
existing_joker = {row[1] for row in cur.execute("PRAGMA table_info(team_matchday_joker)").fetchall()}
print(f"team_matchday_joker colonnes existantes : {existing_joker}")
for col, ddl in [
    ('plays_single', "INTEGER NOT NULL DEFAULT 0"),
    ('plays_double', "INTEGER NOT NULL DEFAULT 0"),
]:
    if col not in existing_joker:
        cur.execute(f"ALTER TABLE team_matchday_joker ADD COLUMN {col} {ddl}")
        print(f"  + Colonne ajoutée : {col}")
    else:
        print(f"  = Déjà présente   : {col}")

conn.commit()
conn.close()
print("\nMigration terminée avec succès.")


