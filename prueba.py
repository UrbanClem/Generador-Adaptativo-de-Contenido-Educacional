import psycopg2

try:
    conexion = psycopg2.connect(
        dbname="rag_education",
        user="postgres",
        password="tu_contraseña",
        host="localhost",
        port="5432"
    )
    print("✅ Conexión exitosa a PostgreSQL")
    conexion.close()
except Exception as e:
    print("❌ Error al conectar:", e)