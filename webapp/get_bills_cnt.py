import sqlite3

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

db = 'bills.db'
conn = sqlite3.connect(db)
conn.row_factory = dict_factory
conn.text_factory = bytes
cursor = conn.cursor()
table_name = 'bills'

q = 'SELECT * FROM {}'.format(table_name)
cursor.execute(q)

res = list(cursor)
print(len(res))
