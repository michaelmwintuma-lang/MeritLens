import sqlite3
con = sqlite3.connect('backend/instance/app.db')
cur = con.cursor()
hr_users = cur.execute("SELECT id, username, full_name, email, role, is_active FROM users WHERE role='hr'").fetchall()
print('HR accounts:')
for r in hr_users:
    print(' ', r)
