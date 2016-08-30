from ftplib import FTP
import config
import re
import time
import os
import asyncio
from pprint import pprint
import logging


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
    rel_path_list = trans_abs_to_rel(config.local_dir,tmppath,os.sep)
    rel_path = "~"
    for x in rel_path_list:
        rel_path += '/' + x

    return dict(
        abs_path    = tmppath,
        rel_path    = rel_path,
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
        newpath = path + '/' + info['name']
        info['abs_path'] = newpath
        rel_path_list = trans_abs_to_rel(config.ftp_dir, newpath, '/')
        rel_path = '~'
        for x in rel_path_list:
            rel_path += '/' + x
        info['rel_path'] = rel_path
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
    if cutted_line.__len__()>9: # 如果文件中有空格
        name = ''
        for i in range(8,cutted_line.__len__()):
            name += cutted_line[i]+' '
        name = name[:-1]
    else:
        name = cutted_line[-1]
    ret['auth']         = cutted_line[0]
    ret['name']         = name
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

def pull():
    print('------------------------------------------------')
    print('start pull at {t}\n'.format(t=gen_time()))
    ftp = FTP(config.ftp_ip)
    ftp.encoding = 'utf-8'  # 这一步很重要，如果没有会导致ftp无法解析中文文件名
    ftp.login(user=config.ftp_user,passwd=config.ftp_pwd)
    remote_files = [x for x in remote_iterator(ftp)]
    local_files = [x for x in local_iterator()]

    # 建立任务列表
    tasks = pull_task_gen(remote_files, local_files)

    # 根据任务列表进行更新，上传，删除等操作
    buffsize = 1024
    for task in tasks:
        if task['type'] == 'update' or \
                (task['type'] == 'add' and not task['isdir']): # 普通文件的情况
            local_file = open(task['to_addr'], 'wb')
            ftp.retrbinary('RETR '+task['from_addr'], local_file.write, buffsize) # 写入本地文件

        elif task['type'] == 'add' and task['isdir'] : # 要建立文件夹的情况
            os.mkdir(task['to_addr'])

        elif task['type'] == 'del':
            addr = task['addr']
            if os.path.exists(addr):
                if task['isdir']:
                    os.rmdir(addr)
                else:
                    os.remove(addr)

        else:
            raise RuntimeError('Unknown task types')

    ftp.close()

def pull_task_gen(remote_files, local_files):
    tasks = []
    local_left_files = local_files[:]
    remote_rel_list = [x['rel_path'] for x in remote_files]
    local_rel_list = [x['rel_path'] for x in local_files]
    for remote_file in remote_files:
        remote_rel_path = remote_file['rel_path']
        if remote_rel_path in local_rel_list: # 如果本地有该文件
            local_left_rel_paths = [x['rel_path'] for x in local_left_files]
            local_left_files.pop(local_left_rel_paths.index(remote_rel_path))
            local_file = local_files[local_rel_list.index(remote_rel_path)]
            if local_file['isdir']:
                continue
            if remote_file['mtime'] - local_file['mtime'] > 60 :  # 如果ftp端文件比本地要提前N秒，则进行同步
                task = dict(
                    type        = 'update',
                    from_addr   = remote_file['abs_path'],
                    to_addr     = local_file['abs_path']
                )
                tasks.append(task)
            else:
                pass
        else:   # 如果本地没有文件
            rel_path = remote_file['rel_path']
            rel_path_list = rel_path.split('/')
            rel_path_list = rel_path_list[1:]
            local_abs_path = config.local_dir
            for x in rel_path_list:
                local_abs_path += os.sep + x
            task = dict(
                type        = 'add',
                from_addr   = remote_file['abs_path'],
                to_addr     = local_abs_path,
                isdir       = remote_file['isdir']
            )
            tasks.append(task)

    for left_file in local_left_files[::-1]:
        task = dict(
            type    = 'del',
            addr    = left_file['abs_path'],
            isdir   = left_file['isdir']
        )
        tasks.append(task)
    return tasks

def push():
    print('------------------------------------------------')
    print('start push at {t}\n'.format(t=gen_time()))
    ftp = FTP(config.ftp_ip)
    ftp.encoding = 'utf-8'
    ftp.login(user=config.ftp_user,passwd=config.ftp_pwd)
    remote_files = [x for x in remote_iterator(ftp)]
    local_files = [x for x in local_iterator()]

    tasks = push_task_gen(local_files, remote_files)

    buffsize = 1024
    for task in tasks:
        if task['type'] == 'update' or \
                (task['type'] == 'add' and not task['isdir']): # 普通文件的情况
            local_file = open(task['from_addr'], 'rb')
            print(task['from_addr'])
            ftp.storbinary('STOR ' + task['to_addr'], local_file, buffsize) #  上传文件

        elif task['type'] == 'add' and task['isdir'] : # 要建立文件夹的情况
            ftp.mkd(task['to_addr'])

        elif task['type'] == 'del':
            addr = task['addr']
            if task['isdir']:
                ftp.rmd(addr)
            else:
                print(addr)
                ftp.delete(addr)

    ftp.close()


def push_task_gen(local_files, remote_files):
    tasks = []
    remote_left_files = remote_files[:]
    remote_rel_list = [x['rel_path'] for x in remote_files]
    for local_file in local_files:
        local_rel_path = local_file['rel_path']
        if local_rel_path in remote_rel_list:  # 如果ftp端有该文件
            remote_left_rel_paths = [x['rel_path'] for x in remote_left_files]
            remote_left_files.pop(remote_left_rel_paths.index(local_rel_path))
            remote_file = remote_files[remote_rel_list.index(local_rel_path)]
            if remote_file['isdir']:
                continue
            if local_file['mtime'] - remote_file['mtime'] > 60:
                task = dict(
                    type        = 'update',
                    from_addr   = local_file['abs_path'],
                    to_addr     = remote_file['abs_path']
                )
                tasks.append(task)
            else:
                pass
        else:   # 如果ftp端没有文件
            rel_path = local_file['rel_path']
            rel_path_list = rel_path.split('/')
            rel_path_list = rel_path_list[1:]
            remote_abs_path = config.ftp_dir
            for x in rel_path_list:
                remote_abs_path += '/' + x
            task = dict(
                type        = 'add',
                from_addr   = local_file['abs_path'],
                to_addr     = remote_abs_path,
                isdir       = local_file['isdir']
            )
            tasks.append(task)
    for left_file in remote_left_files[::-1]:
        task = dict(
            type    = 'del',
            addr    = left_file['abs_path'],
            isdir   = left_file['isdir']
        )
        tasks.append(task)
    return tasks

def gen_time():
    t = time.localtime(time.time())
    return time.strftime('%Y-%m-%d %H:%M:%S', t)

push()

# ftp = FTP(config.ftp_ip)
# ftp.encoding = 'utf-8'
# ftp.login(user=config.ftp_user,passwd=config.ftp_pwd)
# for x in remote_iterator(ftp):
#     print(x)
    # pass

