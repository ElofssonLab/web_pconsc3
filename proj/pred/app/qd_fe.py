#!/usr/bin/env python
# Description: daemon to submit jobs and retrieve results to/from remote
#              servers
# 
# submit job, 
# get finished jobids 
# try to retrieve jobs with in finished jobids

# ChangeLog 2015-08-17
#   The number of jobs submitted to remote servers is calculated based on the
#   queries in remotequeue_index.txt files instead of using get_suqlist.cgi
# ChangeLog 2015-08-23 
#   Fixed the bug for re-creating the torun_idx_file, the code should be before
#   the return 1
# ChangeLog 2015-09-07
#   the torun_idx_file is re-created if remotequeue_idx_file is empty but the
#   job is not finished
# ChangeLog 2016-03-04 
#   fix the bug in re-creation of the torun_idx_file, completed_idx_set is
#   strings but range(numseq) is list of integer numbers

import os
import sys
import site

rundir = os.path.dirname(os.path.realpath(__file__))
webserver_root = os.path.realpath("%s/../../../"%(rundir))

activate_env="%s/env/bin/activate_this.py"%(webserver_root)
exec(compile(open(activate_env, "rb").read(), activate_env, 'exec'), dict(__file__=activate_env))
#Add the site-packages of the virtualenv
site.addsitedir("%s/env/lib/python3.7/site-packages/"%(webserver_root))
sys.path.append("%s/env/lib/python3.7/site-packages/"%(webserver_root))

from libpredweb import myfunc
from libpredweb import dataprocess
from libpredweb import webserver_common as webcom
from libpredweb import qd_fe_common as qdcom
from datetime import datetime
from dateutil import parser as dtparser
from pytz import timezone
import time
import requests
import json
import urllib.request, urllib.parse, urllib.error
import shutil
import hashlib
import subprocess
from suds.client import Client
import numpy
import json

from django.conf import settings

TZ = webcom.TZ
os.environ['TZ'] = TZ
time.tzset()

vip_user_list = [
        "nanjiang.shu@scilifelab.se"
        ]

# make sure that only one instance of the script is running
# this code is working 
progname = os.path.basename(__file__)
rootname_progname = os.path.splitext(progname)[0]
lockname = progname.replace(" ", "").replace("/", "-")
import fcntl
lock_file = "/tmp/%s.lock"%(lockname)
fp = open(lock_file, 'w')
try:
    fcntl.lockf(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
except IOError:
    print("Another instance of %s is running"%(progname), file=sys.stderr)
    sys.exit(1)

contact_email = "nanjiang.shu@scilifelab.se"

threshold_logfilesize = 20*1024*1024 #20M

usage_short="""
Usage: %s
"""%(sys.argv[0])

usage_ext="""
Description:
    Daemon to submit jobs and retrieve results to/from remote servers
    run periodically
    At the end of each run generate a runlog file with the status of all jobs

OPTIONS:
  -h, --help    Print this help message and exit

Created 2016-04-25, updated 2016-05-19, Nanjiang Shu
"""
usage_exp="""
"""

basedir = os.path.realpath("%s/.."%(rundir)) # path of the application, i.e. pred/
path_static = "%s/static"%(basedir)
path_log = "%s/static/log"%(basedir)
path_stat = "%s/stat"%(path_log)
path_result = "%s/static/result"%(basedir)
path_md5cache = "%s/static/md5"%(basedir)
path_cache = "%s/static/result/cache"%(basedir)
computenodefile = "%s/config/computenode.txt"%(basedir)
name_cachedir = 'cache'
# it takes quite long time to run for a single PconsC3 job, set the max queued
# number to a small value
gen_errfile = "%s/static/log/%s.err"%(basedir, progname)
gen_logfile = "%s/static/log/%s.log"%(basedir, progname)
black_iplist_file = "%s/config/black_iplist.txt"%(basedir)
finished_date_db = "%s/cached_job_finished_date.sqlite3"%(path_log)
vip_email_file = "%s/config/vip_email.txt"%(basedir)


def PrintHelp(fpout=sys.stdout):#{{{
    print(usage_short, file=fpout)
    print(usage_ext, file=fpout)
    print(usage_exp, file=fpout)#}}}

def main(g_params):#{{{

    submitjoblogfile = "%s/submitted_seq.log"%(path_log)
    runjoblogfile = "%s/runjob_log.log"%(path_log)
    finishedjoblogfile = "%s/finished_job.log"%(path_log)
    loop = 0
    while 1:

        if os.path.exists("%s/CACHE_CLEANING_IN_PROGRESS"%(path_result)):#pause when cache cleaning is in progress
            continue

        # load the config file if exists
        configfile = "%s/config.json"%(basedir)
        config = {}
        if os.path.exists(configfile):
            text = myfunc.ReadFile(configfile)
            config = json.loads(text)

        if rootname_progname in config:
            g_params.update(config[rootname_progname])

        if os.path.exists(black_iplist_file):
            g_params['blackiplist'] = myfunc.ReadIDList(black_iplist_file)
        avail_computenode = webcom.ReadComputeNode(computenodefile) # return value is a dict
        g_params['vip_user_list'] = myfunc.ReadIDList2(vip_email_file,  col=0)
        num_avail_node = len(avail_computenode)

        webcom.loginfo("loop %d"%(loop), gen_logfile)

        isOldRstdirDeleted = False
        if loop % g_params['STATUS_UPDATE_FREQUENCY'][0] == g_params['STATUS_UPDATE_FREQUENCY'][1]:
            qdcom.RunStatistics_basic(webserver_root, gen_logfile, gen_errfile)
            isOldRstdirDeleted = webcom.DeleteOldResult(path_result, path_log,
                    gen_logfile, MAX_KEEP_DAYS=g_params['MAX_KEEP_DAYS'])
            webcom.CleanServerFile(path_static, gen_logfile, gen_errfile)
            webcom.CleanCachedResult(path_static, name_cachedir,  gen_logfile, gen_errfile)

        webcom.ArchiveLogFile(path_log, threshold_logfilesize=threshold_logfilesize) 

        qdcom.CreateRunJoblog(loop, isOldRstdirDeleted, g_params)

        # Get number of jobs submitted to the remote server based on the
        # runjoblogfile
        if os.path.exists(runjoblogfile):
            runjobidlist = myfunc.ReadIDList2(runjoblogfile,0)
        remotequeueDict = {}
        for node in avail_computenode:
            remotequeueDict[node] = []
        for jobid in runjobidlist:
            rstdir = "%s/%s"%(path_result, jobid)
            remotequeue_idx_file = "%s/remotequeue_seqindex.txt"%(rstdir)
            if os.path.exists(remotequeue_idx_file):
                content = myfunc.ReadFile(remotequeue_idx_file)
                lines = content.split('\n')
                for line in lines:
                    strs = line.split('\t')
                    if len(strs)>=5:
                        node = strs[1]
                        remotejobid = strs[2]
                        if node in remotequeueDict:
                            remotequeueDict[node].append(remotejobid)

        cntSubmitJobDict = {} # format of cntSubmitJobDict {'node_ip': INT, 'node_ip': INT}
        for node in avail_computenode:
            queue_method = avail_computenode[node]['queue_method']
            num_queue_job = len(remotequeueDict[node])
            if num_queue_job >= 0:
                cntSubmitJobDict[node] = [num_queue_job,
                        g_params['MAX_SUBMIT_JOB_PER_NODE'], queue_method] #[num_queue_job, max_allowed_job]
            else:
                cntSubmitJobDict[node] = [g_params['MAX_SUBMIT_JOB_PER_NODE'],
                        g_params['MAX_SUBMIT_JOB_PER_NODE'], queue_method] #[num_queue_job, max_allowed_job]

# entries in runjoblogfile includes jobs in queue or running
        hdl = myfunc.ReadLineByBlock(runjoblogfile)
        if not hdl.failure:
            lines = hdl.readlines()
            while lines != None:
                for line in lines:
                    strs = line.split("\t")
                    if len(strs) >= 11:
                        jobid = strs[0]
                        email = strs[4]
                        try:
                            numseq = int(strs[5])
                        except:
                            numseq = 1
                            pass
                        try:
                            numseq_this_user = int(strs[10])
                        except:
                            numseq_this_user = 1
                            pass
                        rstdir = "%s/%s"%(path_result, jobid)
                        finishtagfile = "%s/%s"%(rstdir, "runjob.finish")
                        status = strs[1]
                        webcom.loginfo("CompNodeStatus: %s"%(str(cntSubmitJobDict)), gen_logfile)

                        runjob_lockfile = "%s/%s/%s.lock"%(path_result, jobid, "runjob.lock")
                        if os.path.exists(runjob_lockfile):
                            msg = "runjob_lockfile %s exists, ignore the job %s" %(runjob_lockfile, jobid)
                            webcom.loginfo(msg, gen_logfile)
                            continue

                        if webcom.IsHaveAvailNode(cntSubmitJobDict):
                            if not g_params['DEBUG_NO_SUBMIT']:
                                qdcom.SubmitJob(jobid, cntSubmitJobDict, numseq_this_user, g_params)
                        qdcom.GetResult(jobid, g_params) # the start tagfile is written when got the first result
                        qdcom.CheckIfJobFinished(jobid, numseq, email, g_params)

                lines = hdl.readlines()
            hdl.close()

        webcom.loginfo("sleep for %d seconds"%(g_params['SLEEP_INTERVAL']), gen_logfile)
        time.sleep(g_params['SLEEP_INTERVAL'])
        loop += 1

    return 0
#}}}


def InitGlobalParameter():#{{{
    g_params = {}
    g_params['isQuiet'] = True
    g_params['blackiplist'] = []
    g_params['DEBUG'] = False
    g_params['DEBUG_NO_SUBMIT'] = False
    g_params['SLEEP_INTERVAL'] = 20    # sleep interval in seconds
    g_params['MAX_SUBMIT_JOB_PER_NODE'] = 10
    g_params['MAX_KEEP_DAYS'] = 90
    g_params['STATUS_UPDATE_FREQUENCY'] = [500, 50]  # updated by if loop%$1 == $2
    g_params['FORMAT_DATETIME'] = webcom.FORMAT_DATETIME
    g_params['MAX_TIME_IN_REMOTE_QUEUE'] = 3600*24*30 # one month in seconds
    g_params['UPPER_WAIT_TIME_IN_SEC'] = 60
    g_params['MAX_CACHE_PROCESS'] = 200 # process at the maximum this cached sequences in one loop
    g_params['MAX_RESUBMIT'] = 3
    g_params['name_server'] = "PconsC3"
    g_params['path_static'] = path_static
    g_params['path_result'] = path_result
    g_params['path_log'] = path_log
    g_params['path_cache'] = path_cache
    g_params['vip_email_file'] = vip_email_file
    g_params['gen_logfile'] = gen_logfile
    g_params['finished_date_db'] = finished_date_db
    g_params['gen_errfile'] = gen_errfile
    g_params['contact_email'] = contact_email
    g_params['name_cachedir'] = name_cachedir
    g_params['TZ'] = TZ
    return g_params
#}}}
if __name__ == '__main__' :
    g_params = InitGlobalParameter()
    date_str = time.strftime(g_params['FORMAT_DATETIME'])
    print("\n#%s#\n[Date: %s] qd_fe.py restarted"%('='*80,date_str))
    sys.stdout.flush()
    sys.exit(main(g_params))
