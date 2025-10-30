from src.config.database import execute_query

def main():
    print('total:', execute_query("SELECT COUNT(*) AS total FROM login"))
    print('bcrypt_count:', execute_query("SELECT COUNT(*) AS bcrypt_count FROM login WHERE `contraseña` LIKE '$2%'") )
    print('samples:', execute_query("SELECT correo, LEFT(`contraseña`,60) AS ejemplo_hash FROM login LIMIT 10"))

if __name__ == '__main__':
    main()
