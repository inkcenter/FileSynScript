from ftplib import FTP
import config
import re
import time
import os
import asyncio

# ftp = FTP(config.ftp_ip)
# ftp.login(user=config.ftp_user,passwd=config.ftp_pwd)
# ftp.cwd(config.ftp_dir)
#
#
# def putin(line):
#     yield line
#
# ret = ftp.nlst()
# s =[]
# ftp.retrlines("LIST",s.append)
# print(s)
# ftp.putcmd("delete README")
# print(ftp.getline())



@asyncio.coroutine
def local_iterator(path=config.local_dir):
    file_paths = os.listdir(path)
    for file_path in file_paths:
        tmppath = os.path.join(path,file_path)
        if os.path.isdir(tmppath):
            yield from local_iterator(tmppath)
        else:
            os_stat = os.stat(tmppath)
            st_mtime = os_stat.st_mtime
            yield dict(
                path    = tmppath,
                mtime   = st_mtime,
                size    = os_stat.st_size
            )

def remote_iterator(conn, path=config.ftp_dir):
    lines = []
    conn.retrlines("LIST", lines.append)
    print(lines)

def parse_ftp_info(line):
    ret = {}
    current_year = 2016
    line = re.sub(r"\s+",' ',line)
    cutted_line = line.split(' ')
    ret['auth']         = cutted_line[0]
    ret['name']         = cutted_line[-1]
    ret['time_str']     = '{y}-{m}-{d}-{t}'.format( y=current_year,
                                                    m=cutted_line[5],
                                                    d=cutted_line[6],
                                                    t=cutted_line[7])
    ret['timestamp']    = int(time.mktime(time.strptime(ret['time_str'], '%Y-%b-%d-%H:%M')))
    ret['isdir']        = 'd' in ret['auth']
    print(ret)
    return ret
# ftp.mkd('TEST')

info = ['-rw-------    1 1001     1001         5614 Aug 29 09:38 README', 'drwx------    2 1001     1001         4096 Aug 29 11:41 TEST']
ftp = FTP(config.ftp_ip)
ftp.login(user=config.ftp_user,passwd=config.ftp_pwd)
remote_iterator(ftp)