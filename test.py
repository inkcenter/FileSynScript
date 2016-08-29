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
            try:
                yield local_stat(tmppath)
                yield from local_iterator(tmppath)
            except:
                pass
        else:
            try:
                yield local_stat(tmppath)
            except Exception as e:
                pass

def local_stat(tmppath):
    os_stat = os.stat(tmppath)
    st_mtime = os_stat.st_mtime
    return dict(
        abs_path    = tmppath,
        rel_path    = trans_abs_to_rel(config.local_dir,tmppath,os.sep),
        mtime       = int(st_mtime),
        size        = os_stat.st_size,
        isdir       = os.path.isdir(tmppath)
    )

@asyncio.coroutine
def remote_iterator(conn, path=config.ftp_dir):
    conn.cwd(path)
    lines = []
    abs_path = conn.pwd()
    conn.retrlines("LIST", lines.append)
    for line in lines:
        conn.cwd(path)
        info = parse_ftp_info(line)
        newpath = path + r'/' + info['name']
        info['abs_path'] = newpath
        if info['isdir']:
            yield info
            yield from remote_iterator(conn, path=newpath)
        else:
            # print(path)
            yield info

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
    ret['mtime']    = int(time.mktime(time.strptime(ret['time_str'], '%Y-%b-%d-%H:%M')))
    ret['isdir']        = 'd' in ret['auth']
    return ret
# ftp.mkd('TEST')

def trans_abs_to_rel(par_p,abs_p,sep):
    par_l = par_p.split(sep)
    abs_l = abs_p.split(sep)
    rel_l = abs_l[par_l.__len__():]
    return rel_l

info = ['-rw-------    1 1001     1001         5614 Aug 29 09:38 README', 'drwx------    2 1001     1001         4096 Aug 29 11:41 TEST']
ftp = FTP(config.ftp_ip)
ftp.login(user=config.ftp_user,passwd=config.ftp_pwd)
for x in remote_iterator(ftp):
    print(x)

for x in local_iterator():
    print(x)
