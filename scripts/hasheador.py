import pymysql
import bcrypt

conn = pymysql.connect(
    host="db",
    user="root",
    password="rootpassword",
    database="proyecto",
    port=3306,
    autocommit=True
)

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def main():

    with conn.cursor() as cur:
        cur.execute("SELECT correo, contrasena FROM login")
        rows = cur.fetchall()

        for correo, pwd in rows:
            if pwd is None:
                continue

            if pwd.startswith("$2"):
                print(f"[OK] {correo} ya tiene bcrypt")
                continue

            print(f"[HASH] {correo}: '{pwd}' → bcrypt")
            new_hash = hash_password(pwd)

            cur.execute(
                "UPDATE login SET contrasena = %s WHERE correo = %s",
                (new_hash, correo)
            )


if __name__ == "__main__":
    main()
