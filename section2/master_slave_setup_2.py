#!/usr/bin/env python

from optparse import OptionParser
import psycopg2
from fabric.api import run, local, env, settings
import getpass
import time
import datetime
import os, sys

use = "Usage: python master_slave_setup_2.py [-p --port] [-u --user] [-s --slave-hostname] [-t --target] hostname prod(yes/no) "
port = 0
user = ""
target = 100000
slv = ""
hst = ""
db_port = 5432
xlog_loc = ""

def run_rsync():
    rsync_cmd = open('rsync.sh', 'w') 
    rsync_cmd.write('rsync -av /pgdata -e "ssh -i ~/.ssh/id_rsa -p %(p)s -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no" --delete --exclude server.crt --exclude server.key --exclude recovery.done --exclude postmaster.pid --exclude archive --exclude backup_label %(s)s:/' % {"h": hst, "s": slv, "p": port});
    rsync_cmd.close()
    local('scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -P %(p)s rsync.sh %(u)s@%(h)s:~/'% {"h": hst, "u": user, "p": port})	
    with settings(host_string=hst,  user=user, port=port, use_ssh_config = False, always_use_pty=True, warn_only=True, pty=True, sudo_prefix=True):
        run('sudo mv ~/rsync.sh ~postgres/')
        run('sudo chown postgres.postgres ~postgres/rsync.sh')
        run('sudo -u postgres sh ~postgres/rsync.sh')
#     with settings(host_string=hst,  user="postgres", port=port, use_ssh_config = False, always_use_pty=True, warn_only=True, pty=True, sudo_prefix=True):
    with settings(host_string=slv, user=user, port=port, use_ssh_config = True, always_use_pty=True, warn_only=False, pty=True, sudo_prefix=True):	
        rec = open('recovery.conf', 'w+')
        rec_str = "standby_mode = 'on'\n\
primary_conninfo = 'host=%(h)s user=repuser keepalives_idle=8'\n\
trigger_file = '/tmp/postgresql.trigger.5432' " % {"h": hst}
        rec.write(rec_str)
        rec.close()
        local('scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -P %(p)s recovery.conf %(u)s@%(h)s:~/' % {"h": slv, "u":user, "p": port})
        local('scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -P %(p)s postgresqlconfedit.sh %(u)s@%(h)s:~/' % {"h": slv, "u":user, "p": port})
        run('sudo mv ~/recovery.conf /pgdata')
    with settings(host_string=slv, user=user, port=port, use_ssh_config = True, always_use_pty=True, warn_only=False, pty=True, sudo_prefix=True):	
        run('sudo chown -R postgres.postgres /pgdata')
        run('sh ~/postgresqlconfedit.sh')
        run('sh ~/pg_ctl_start.sh')        
    time.sleep(60)
    with settings(host_string=hst,  user=user, port=port, use_ssh_config = False, always_use_pty=True, warn_only=True, pty=True, sudo_prefix=True):
        run('sudo -u postgres psql -c "select pg_stop_backup(), current_timestamp" gameplace postgres')
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
#     if sys.stdin.isatty():
#         pw = getpass.getpass()
#     else:
#         pw=sys.stdin.readline().rstrip()
    if prod == 'yes':
    	db_port = 6453
    run_rsync()
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
