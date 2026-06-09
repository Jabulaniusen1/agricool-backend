from utils import setup_connection

with open("schema/init_tables.sql", "r") as f:
    sql = f.read()

 
conn = setup_connection()
try:
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
    print("Metrics tables created successfully")
finally:
    cur.close()
    conn.close()