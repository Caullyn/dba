#!/usr/bin/env python

from optparse import OptionParser
import psycopg2
from fabric.api import run, local, env, settings
import getpass
import time
import datetime
import os, sys

use = "Usage: python master_slave_setup_1.py [-p --port] [-u --user] [-s --slave-hostname] [-t --target] hostname prod(yes/no) "
port = 0
user = ""
target = 100000
slv = ""
hst = ""
db_port = 5432
xlog_loc = ""

def install_dir(host):
    global port, user
    print 'Installing directories and PostgreSQL on %(h)s...' % {"h": host}
    with settings(host_string=host, user=user, port=port, use_ssh_config = True, always_use_pty=False, warn_only=True, pty=True, sudo_prefix=True):
    	run('sudo ufw disable')
    	run('sudo service ufw stop')
        run('sudo apt-get update')
#         time.sleep(10)
        run('sudo apt-get install -y postgresql-9.3')
        run('sudo mkdir /pgdata')
        run('sudo mkdir /pglog')
        run('sudo mkdir /pglog/archive')
        run('sudo mkdir /pgbackup')
        run('sudo chown -R postgres.postgres /pgdata')
        run('sudo chown -R postgres.postgres /pglog')
        run('sudo chown -R postgres.postgres /pgbackup')
        run('sudo -u postgres /usr/lib/postgresql/9.3/bin/pg_ctl stop -w -D /var/lib/postgresql/9.3/main')
def config_db():
    global hst, prod, user
    print 'Configuring DB'
    with settings(host_string=hst, user=user, port=port, use_ssh_config = True, always_use_pty=False, warn_only=True, pty=True, sudo_prefix=True):
        run('sudo -u postgres /usr/lib/postgresql/9.3/bin/initdb -D /pgdata')
    local('scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -P %(p)s pg_ctl_start.sh %(u)s@%(h)s:~/'% {"h": hst, "u":user, "p": port})
    if prod == 'no':
        local('scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -P %(p)s postgresql.conf %(u)s@%(h)s:~/' % {"h": hst, "u":user, "p": port})
        local('scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -P %(p)s pg_hba.conf %(u)s@%(h)s:~/'% {"h": hst, "u":user, "p": port})
        local('scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -P %(p)s sysctl.conf %(u)s@%(h)s:~/'% {"h": hst, "u":user, "p": port})
    else:
        local('scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -P %(p)s postgresql_prod.conf %(u)s@%(h)s:~/postgresql.conf' % {"h": hst, "u":user, "p": port})
        local('scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -P %(p)s pg_hba_prod.conf %(u)s@%(h)s:~/pg_hba.conf'% {"h": hst, "u":user, "p": port})
        local('scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -P %(p)s sysctl_prod.conf %(u)s@%(h)s:~/sysctl.conf'% {"h": hst, "u":user, "p": port})
    with settings(host_string=hst,   user=user, port=port, use_ssh_config = True, always_use_pty=True, warn_only=True, pty=True, sudo_prefix=True):
        run('sudo mv ~/sysctl.conf /etc/')
        run('sudo chown root.root /etc/sysctl.conf')
        run('sudo sysctl -p')
        time.sleep(5)
        run('sudo mv postgresql.conf /pgdata')
        run('sudo mv pg_hba.conf /pgdata')  
        run('sudo chown postgres.postgres /pgdata/postgresql.conf')
        run('sudo chown postgres.postgres /pgdata/pg_hba.conf')
        run('sudo chown postgres.postgres ~postgres/pg_ctl_start.sh')
        run('sh pg_ctl_start.sh')
        #run('sudo -u postgres /usr/pgsql-9.2/bin/pg_ctl start -D /pgdata ')
        time.sleep(25)
        dbcon = psycopg2.connect(dbname="postgres", user="postgres", password="postgres", host=hst, port=db_port)
        dbcon.set_isolation_level(0)
        cur = dbcon.cursor()
        print 'creating databases'
        cur.execute('CREATE DATABASE gameplace;')
        dbcon.commit()
        cur.close()
        dbcon.close()
def build_slave():
    global hst, slv, db_port, xlog_loc
    dbcon = psycopg2.connect(dbname="postgres", user="postgres", password="postgres", host=hst, port=db_port)
    dbcon.set_isolation_level(0)
    cur = dbcon.cursor()
    cur.execute("select pg_start_backup('base backup for streaming rep')")
    xlog_loc = cur.fetchone()
    cur.execute("create ROLE repuser SUPERUSER LOGIN CONNECTION LIMIT 1 ENCRYPTED PASSWORD '%(p)s'" % {"p": "4rVR4$e#"})
    dbcon.commit()
    cur.close()
    dbcon.close()	
    local('scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -P %(p)s pg_ctl_start.sh %(u)s@%(h)s:~/'% {"h": slv, "u":user, "p": port})	
    print '========================================================================================'
    print ' Set up SSH keys between postgres users on each box, then run master_slave_setup_2.py'
    print '========================================================================================'   
try:
    parser = OptionParser(usage = use)
    parser.add_option("-p", "--port",
                 action="store",  default="53424", 
                 dest="port", help="ssh port")
    parser.add_option("-u", "--user",
                 action="store",   
                 dest="user", help="linux username")
    parser.add_option("-s", "--slave-hostname",
                 action="store",   
                 dest="slv", help="hostname of slave")
    parser.add_option("-t", "--target",
                 action="store",   
                 dest="target", help="schema version to deploy")
    options, args = parser.parse_args()
    hst = "{0}".format(args[0])
    prod = "{0}".format(args[1])
    port = options.port
    user = options.user
    slv = options.slv
    target = options.target
    print hst
    print slv
    install_dir(hst)
    config_db()
    install_dir(slv)
    build_slave()
except Exception, e:
    print type(e)
    print e.args
    print e
    print '---------------------------------------------------------------------------'
    print ' '
    print 'deploy_cloud.py'
    print ' '
    print use
    print ' '
    print '---------------------------------------------------------------------------'
