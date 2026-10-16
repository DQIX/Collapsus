import sqlite3

import parsers


def create_table():
    conn = sqlite3.connect('grottos.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS grottos (
                name text,
                url text,
                special int,
                seed text,
                rank text,
                type text,
                floors text,
                boss text,
                monster_rank text,
                chests text,
                locations text,
                notes text,
                owner text
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS search_counts (
                user_id text PRIMARY KEY,
                count int
                )''')
    conn.commit()
    conn.close()


def increment_search_count(user_id):
    conn = sqlite3.connect('grottos.db')
    c = conn.cursor()

    c.execute('''INSERT INTO search_counts VALUES (?, 1)
                 ON CONFLICT(user_id) DO UPDATE SET count = count + 1''', (str(user_id),))
    c.execute('''SELECT count FROM search_counts WHERE user_id = ?''', (str(user_id),))
    count = c.fetchone()[0]
    conn.commit()
    conn.close()

    return count


def insert_grotto(grotto):
    conn = sqlite3.connect('grottos.db')
    c = conn.cursor()

    c.execute('''INSERT INTO grottos VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (
        grotto.name, grotto.url, grotto.special, grotto.seed, grotto.rank, grotto.type, grotto.floors, grotto.boss,
        grotto.monster_rank, grotto.chests, grotto.locations, grotto.notes, grotto.owner))
    conn.commit()
    conn.close()


def update_grotto(user_id, old_note, new_note):
    conn = sqlite3.connect('grottos.db')
    c = conn.cursor()

    c.execute('''UPDATE grottos SET notes = ? WHERE owner = ? AND notes = ?''', (new_note, user_id, old_note))
    conn.commit()
    conn.close()

    return c.rowcount > 0


def delete_grotto(user_id, grotto_note):
    conn = sqlite3.connect('grottos.db')
    c = conn.cursor()

    c.execute('''DELETE FROM grottos WHERE owner = ? AND notes = ?''', (user_id, grotto_note))
    conn.commit()
    conn.close()

    return c.rowcount > 0


def get_grottos(user_id, all_grottos=False):
    if all_grottos and user_id == 496392770374860811:
        conn = sqlite3.connect('grottos.db')
        c = conn.cursor()

        c.execute('''SELECT * FROM grottos''')
        grottos_db = c.fetchall()

        conn.close()
        grottos = [parsers.Grotto(*grotto) for grotto in grottos_db]
        return grottos

    conn = sqlite3.connect('grottos.db')
    c = conn.cursor()

    c.execute('''SELECT * FROM grottos WHERE owner = ?''', (user_id,))
    grottos_db = c.fetchall()

    conn.close()
    grottos = [parsers.Grotto(*grotto) for grotto in grottos_db]
    return grottos


def get_grotto(user_id, grotto_note):
    conn = sqlite3.connect('grottos.db')
    c = conn.cursor()

    c.execute('''SELECT * FROM grottos WHERE owner = ? AND notes = ?''', (user_id, grotto_note))
    grotto_db = c.fetchone()

    conn.close()
    return parsers.Grotto(*grotto_db) if grotto_db else None


def confirm_unique_note(user_id, note):
    conn = sqlite3.connect('grottos.db')
    c = conn.cursor()

    c.execute('''SELECT * FROM grottos WHERE owner = ? AND notes = ?''', (user_id, note))
    grottos_db = c.fetchall()

    conn.close()
    return len(grottos_db) == 0
