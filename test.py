from ftplib import FTP
import config


ftp = FTP(config.ftp_ip)
ftp.login(user=config.ftp_user,passwd=config.ftp_pwd)
ftp.cwd(config.ftp_dir)

print(ftp.retrlines('LIST'))
# ftp.putcmd("delete README")
# print(ftp.getline())