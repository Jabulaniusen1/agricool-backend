from utils import setup_connection

with open("create_tables.sql", "r") as f:
    sql = f.read()

 
conn = setup_connection()
try:
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
    print("Farmer metrics tables created successfully")
finally:
    cur.close()
    conn.close()