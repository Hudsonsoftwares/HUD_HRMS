import psycopg2
try:
    conn = psycopg2.connect(host="localhost", dbname="HRMS", user="odoo", password="odoopwd")
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'hr_employee';")
    cols = cur.fetchall()
    print("Columns in hr_employee:")
    for col in cols:
        print(f"  {col[0]}: {col[1]}")
    conn.close()
except Exception as e:
    print("Error:", e)
