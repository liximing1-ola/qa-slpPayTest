# coding=utf-8
"""种子数据快照：导出 / 列出 / 恢复

要解决的问题：余额、背包、等级、上周厅这些都能由用例前置重造，但账号、房间、工会、
礼物配置是造数的前提——账号被清理后，连 update 都不知道往哪一行写。所以只把这几张
「种子表」里测试账号相关的行导出来，几十 KB，几分钟能恢复。

几条刻意的选择：
- 存仓库外（默认 ~/.slp_backup）：快照里有手机号，不能跟着代码进 git
- 文件权限 600：同上
- 密码走 MYSQL_PWD 环境变量，不进命令行：否则 ps 里能看到
- 小表整表导、大表按 id 过滤：小表猜错过滤列名的代价是把环境恢复坏，不划算
- 恢复必须带 --yes 或手动输入确认：这条命令会覆盖线上测试库
- --dry-run 只打印命令：本机（Windows）连不上库时也能先确认命令拼得对不对

用法：
    python backup_seed.py dump --dry-run        # 先看会执行什么
    python backup_seed.py dump                 # 导出，默认保留最近 4 份
    python backup_seed.py list                 # 看已有快照
    python backup_seed.py restore ~/.slp_backup/seed-2026-10-29-100000.sql --yes
"""
import argparse
import glob
import os
import shutil
import subprocess
import sys
from datetime import datetime

DEFAULT_OUT = os.path.join(os.path.expanduser('~'), '.slp_backup')
DEFAULT_KEEP = 4


def dump_targets():
    """[(表, 过滤列, 过滤值)]：只含主库 xianshi

    过滤列与体检清单共用同一批 id，避免两边各自漂移。过滤列为 None 表示整表导出：
    小表（礼物、商品、房间配置）整表导，不为省几 KB 去猜列名——猜错就是把环境恢复坏。
    config 库的白名单单独成文件，见 config_targets。
    """
    from common.envData import SEED_BROKERS, SEED_ROOMS, SEED_USERS

    return [
        ('xs_user_index', 'uid', SEED_USERS),
        ('xs_user_profile', 'uid', SEED_USERS),
        ('xs_user_mobile', 'uid', SEED_USERS),
        ('xs_broker', 'bid', SEED_BROKERS),
        ('xs_broker_user', 'uid', SEED_USERS),
        ('xs_chatroom', 'rid', SEED_ROOMS),
        ('xs_chatroom_config', None, None),
        ('xs_gift', None, None),
        ('xs_commodity', None, None),
    ]


def config_targets():
    """跨库的那一张：单独成文件，恢复时才能指定正确的库名

    mysqldump 的输出里 INSERT 不带库前缀，两个库混在一个文件里就没法用一次 mysql
    导入完——指定 xianshi 会报「表不存在」，不指定会报「no database selected」。
    """
    return [('xsst_ktv_uid_white', None, None)]


def db_args():
    """连接参数只从 conSlpXsgMysql 取一份：换环境时只改它，这里跟着走"""
    from common.conSlpXsgMysql import conMysql
    db = conMysql.db_config
    return db['ali_db'], db['ali_user'], db['ali_pas']


def dump_command(host, user, database, table, column, values):
    command = ['mysqldump', '-h', host, '-P', '3306', '-u', user,
               '--single-transaction', '--skip-add-locks', '--no-tablespaces',
               '--skip-extended-insert', '--default-character-set=utf8mb4',
               database, table]
    if column:
        command.append('--where={} in ({})'.format(column, ','.join(str(v) for v in values)))
    return command


def run_dump(out_dir=DEFAULT_OUT, keep=DEFAULT_KEEP, dry_run=False):
    host, user, password = db_args()
    # dry-run 不依赖 mysqldump：本机（Windows）一般没装，而确认命令拼得对不对正是它的用途
    if not shutil.which('mysqldump') and not dry_run:
        print('找不到 mysqldump，请先安装 mysql 客户端，或用 --dry-run 只看命令', flush=True)
        return 1
    if not dry_run and not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    stamp = datetime.now().strftime('%Y-%m-%d-%H%M%S')
    # 两个库分两个文件：mysqldump 的 INSERT 不带库前缀，混在一个文件里就没法一次导入
    plan = [
        ('seed-{}.sql'.format(stamp), 'xianshi', dump_targets()),
        ('seed-config-{}.sql'.format(stamp), 'config', config_targets()),
    ]
    env = dict(os.environ, MYSQL_PWD=password)
    printed, failed = [], []

    for name, database, targets in plan:
        path = os.path.join(out_dir, name)
        handle = None if dry_run else open(path, 'w', encoding='utf-8')
        try:
            if handle:
                handle.write('-- 种子数据快照 {}（{} 库）\n'.format(stamp, database))
                handle.write('-- 表：{}\n\n'.format(', '.join(item[0] for item in targets)))
            for table, column, values in targets:
                command = dump_command(host, user, database, table, column, values)
                printed.append(' '.join(command))
                if dry_run:
                    continue
                print('[备份] {}.{}'.format(database, table), flush=True)
                done = subprocess.run(command, stdout=handle, stderr=subprocess.PIPE, env=env)
                # 单表失败不能让整份快照作废，但必须打出来，否则「恢复后还是缺」成了新谜题
                if done.returncode != 0:
                    lines = done.stderr.decode('utf-8', 'ignore').strip().splitlines()
                    failed.append('{}.{}: {}'.format(
                        database, table, (lines[-1] if lines else '未知错误')[:120]))
        finally:
            if handle:
                handle.close()
                try:
                    os.chmod(path, 0o600)
                except OSError:
                    pass  # Windows 上权限位无效，目录的访问控制仍然有效
                if os.path.getsize(path) > 0:
                    print('[备份] 已写出 {}（{} KB）'.format(
                        path, round(os.path.getsize(path) / 1024, 1)), flush=True)

    if dry_run:
        print('将要执行（未实际运行）：', flush=True)
        for line in printed:
            print('  ' + line, flush=True)
        return 0
    if failed:
        print('[备份] {} 张表导出失败：\n  {}'.format(len(failed), '\n  '.join(failed)), flush=True)
    rotate(out_dir, keep)
    return 1 if failed else 0


def rotate(out_dir, keep):
    """只留最近 keep 份：快照是为了恢复最近的一次事故，不是做归档

    只按主快照计数（seed-数字...），config 那份跟着同一轮的主快照一起删——
    两种文件名混在一起排序，会把 config 当成更新的而误留。
    """
    files = sorted(glob.glob(os.path.join(out_dir, 'seed-[0-9]*.sql')))
    for old in files[:-keep] if keep > 0 else []:
        os.remove(old)
        print('[备份] 轮转删除 {}'.format(os.path.basename(old)), flush=True)
        config = os.path.join(os.path.dirname(old),
                              os.path.basename(old).replace('seed-', 'seed-config-', 1))
        if os.path.isfile(config):
            os.remove(config)
            print('[备份] 轮转删除 {}'.format(os.path.basename(config)), flush=True)


def run_list(out_dir=DEFAULT_OUT):
    files = sorted(glob.glob(os.path.join(out_dir, 'seed-*.sql')))
    if not files:
        print('{} 下没有快照'.format(out_dir), flush=True)
        return 0
    for path in files:
        stat = os.stat(path)
        print('{:<44} {:>8.1f} KB  {}'.format(
            os.path.basename(path), stat.st_size / 1024,
            datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')), flush=True)
    return 0


def run_restore(path, assume_yes=False, dry_run=False):
    if not os.path.isfile(path):
        print('快照不存在：{}'.format(path), flush=True)
        return 1
    host, user, password = db_args()

    # 主快照按 xianshi 导入，同名 config 快照（如果有）按 config 导入。
    # 传哪个都行：传 seed-config-xxx 会先换算回主文件。
    main_path = path.replace('seed-config-', 'seed-', 1)
    if not os.path.isfile(main_path):
        main_path = path
    pairs = [(main_path, 'xianshi')]
    config_path = os.path.join(os.path.dirname(main_path),
                               os.path.basename(main_path).replace('seed-', 'seed-config-', 1))
    if os.path.isfile(config_path):
        pairs.append((config_path, 'config'))

    print('将恢复到 {}：{}'.format(
        host, '、'.join('{} -> {}'.format(os.path.basename(item), db) for item, db in pairs)),
        flush=True)
    if not assume_yes and not dry_run:
        answer = input('确认覆盖线上测试库？输入 RESTORE 继续：').strip()
        if answer != 'RESTORE':
            print('已取消', flush=True)
            return 1

    env = dict(os.environ, MYSQL_PWD=password)
    for sql_path, database in pairs:
        command = ['mysql', '-h', host, '-P', '3306', '-u', user, database]
        if dry_run:
            print('将要执行（未实际运行）： {} < {}'.format(' '.join(command), sql_path), flush=True)
            continue
        print('[恢复] {} -> {}'.format(os.path.basename(sql_path), database), flush=True)
        with open(sql_path, 'rb') as handle:
            done = subprocess.run(command, stdin=handle, stderr=subprocess.PIPE, env=env)
        if done.returncode != 0:
            print('[恢复] 失败：{}'.format(
                done.stderr.decode('utf-8', 'ignore').strip()[:300]), flush=True)
            return 1
    if dry_run:
        return 0
    print('[恢复] 完成，接着跑 python -m common.preflight slp 确认种子齐全', flush=True)
    return 0


def main():
    parser = argparse.ArgumentParser(description='测试环境种子数据快照')
    sub = parser.add_subparsers(dest='action')
    dump_parser = sub.add_parser('dump', help='导出快照')
    dump_parser.add_argument('--out', default=DEFAULT_OUT)
    dump_parser.add_argument('--keep', type=int, default=DEFAULT_KEEP)
    dump_parser.add_argument('--dry-run', action='store_true')
    list_parser = sub.add_parser('list', help='列出已有快照')
    list_parser.add_argument('--out', default=DEFAULT_OUT)
    restore_parser = sub.add_parser('restore', help='从快照恢复')
    restore_parser.add_argument('file')
    restore_parser.add_argument('--yes', action='store_true')
    restore_parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    if args.action == 'dump':
        return run_dump(args.out, args.keep, args.dry_run)
    if args.action == 'list':
        return run_list(args.out)
    if args.action == 'restore':
        return run_restore(args.file, args.yes, args.dry_run)
    parser.print_help()
    return 0


if __name__ == '__main__':
    sys.exit(main())
