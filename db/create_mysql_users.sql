DROP USER IF EXISTS 'app_readonly'@'%';
DROP USER IF EXISTS 'app_user'@'%';
DROP USER IF EXISTS 'app_admin'@'%';

CREATE USER 'app_readonly'@'%' IDENTIFIED BY 'readonly_pass_2025';
CREATE USER 'app_user'@'%' IDENTIFIED BY 'user_pass_2025';
CREATE USER 'app_admin'@'%' IDENTIFIED BY 'admin_pass_2025';

GRANT SELECT ON proyecto.* TO 'app_readonly'@'%';
GRANT SELECT, INSERT, UPDATE ON proyecto.* TO 'app_user'@'%';
GRANT ALL PRIVILEGES ON proyecto.* TO 'app_admin'@'%';

FLUSH PRIVILEGES;
