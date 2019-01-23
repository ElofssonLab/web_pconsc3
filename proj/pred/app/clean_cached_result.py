#!/usr/bin/env python

import sys
import os
import sqlite3
import shutil
import argparse

import time
from datetime import datetime
from pytz import timezone
import tempfile
import myfunc
import webserver_common

FORMAT_DATETIME = webserver_common.FORMAT_DATETIME
TZ = webserver_common.TZ

progname=os.path.basename(sys.argv[0])
rootname_progname = os.path.splitext(progname)[0]
lockname = os.path.realpath(__file__).replace(" ", "").replace("/", "-")
import fcntl
lock_file = "/tmp/%s.lock"%(lockname)
fp = open(lock_file, 'w')
try:
    fcntl.lockf(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
except IOError:
    print >> sys.stderr, "Another instance of %s is running"%(progname)
    sys.exit(1)


rundir = os.path.dirname(os.path.realpath(__file__))
basedir = os.path.realpath("%s/.."%(rundir)) # path of the application, i.e. pred/
path_log = "%s/static/log"%(basedir)
path_stat = "%s/stat"%(path_log)
path_result = "%s/static/result"%(basedir)
path_cache = "%s/static/result/cache"%(basedir)
gen_logfile = "%s/%s.log"%(path_log, progname)
gen_errfile = "%s/%s.err"%(path_log, progname)

def CleanCachedResult(MAX_KEEP_DAYS):# {{{
    """Clean out-dated cached result"""
    db = "%s/cached_job_finished_date.sqlite3"%(path_log)
    tmpdb = tempfile.mktemp(prefix="%s_"%(db))

    msg = "copy db (%s) to tmpdb (%s)"%(db, tmpdb)
    date_str = time.strftime(FORMAT_DATETIME)
    myfunc.WriteFile("[%s] %s\n"%(date_str, msg), gen_logfile, "a", True)
    try:
        shutil.copyfile(db,tmpdb)
    except Exception as e:
        myfunc.WriteFile("[%s] %s\n"%(date_str, str(e)), gen_errfile, "a", True)
        return 1

    md5listfile = "%s/cache_to_delete.md5list"%(path_log)
    con = sqlite3.connect(tmpdb)
    msg =  "output the outdated md5 list to %s"%(md5listfile)
    date_str = time.strftime(FORMAT_DATETIME)
    myfunc.WriteFile("[%s] %s\n"%(date_str, msg), gen_logfile, "a", True)

    tablename = "data"

    with con:
        cur = con.cursor()
        fpout = open(md5listfile, "w")
        nn_mag = cur.execute("SELECT md5, date_finish FROM %s"%(tablename))
        cnt = 0 
        chunk_size = 1000
        while True:
            result = nn_mag.fetchmany(chunk_size)
            if not result:
                break
            else:
                for row in result:
                    cnt += 1
                    md5_key = row[0]
                    finish_date_str = row[1]
                    finish_date = webserver_common.datetime_str_to_time(finish_date_str)
                    current_time = datetime.now(timezone(TZ))
                    timeDiff = current_time - finish_date
                    if timeDiff.days > MAX_KEEP_DAYS:
                        fpout.write("%s\n"%(md5_key))
        fpout.close()


        # delete cached result folder and delete the record
        msg = "Delete cached result folder and delete the record"
        date_str = time.strftime(FORMAT_DATETIME)
        myfunc.WriteFile("[%s] %s\n"%(date_str, msg), gen_logfile, "a", True)

        hdl = myfunc.ReadLineByBlock(md5listfile)
        lines = hdl.readlines()
        cnt = 0
        while lines != None:
            for line in lines:
                line = line.strip()
                if line != "":
                    cnt += 1
                    md5_key = line

                    subfoldername = md5_key[:2]
                    cachedir = "%s/%s/%s"%(path_cache, subfoldername, md5_key)
                    zipfile_cache = cachedir + ".zip"
                    date_str = time.strftime(FORMAT_DATETIME)
                    if os.path.exists(zipfile_cache):
                        try:
                            os.remove(zipfile_cache)
                            msg = "rm %s"%(zipfile_cache)
                            myfunc.WriteFile("[%s] %s\n"%(date_str, msg), gen_logfile, "a", True)
                            cmd_d = "DELETE FROM %s WHERE md5 = '%s'"%(tablename, md5_key)
                            cur.execute(cmd_d)
                        except Exception as e:
                            myfunc.WriteFile("[%s] %s\n"%(date_str, str(e)), gen_errfile, "a", True)
                            pass

            lines = hdl.readlines()
        hdl.close()

        msg =  "VACUUM the database %s"%(tmpdb)
        date_str = time.strftime(FORMAT_DATETIME)
        myfunc.WriteFile("[%s] %s\n"%(date_str, msg), gen_logfile, "a", True)
        cur.execute("VACUUM")

    # copy back
    msg = "cp tmpdb (%s) -> db (%s)"%(tmpdb, db)
    date_str = time.strftime(FORMAT_DATETIME)
    myfunc.WriteFile("[%s] %s\n"%(date_str, msg), gen_logfile, "a", True)
    try:
        shutil.copyfile(tmpdb, db)
    except Exception as e:
        myfunc.WriteFile("[%s] %s\n"%(date_str, str(e)), gen_errfile, "a", True)
        return 1

    msg = "delete tmpdb (%s)"%(tmpdb)
    date_str = time.strftime(FORMAT_DATETIME)
    myfunc.WriteFile("[%s] %s\n"%(date_str, msg), gen_logfile, "a", True)
    try:
        os.remove(tmpdb)
    except Exception as e:
        myfunc.WriteFile("[%s] %s\n"%(date_str, str(e)), gen_errfile, "a", True)
        return 1


# }}}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
            description='Clean outdated cached results',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog='''\
Created 2018-10-21, updated 2018-10-21, Nanjiang Shu

Examples:
    %s -max-keep-day 360
'''%(sys.argv[0]))
    parser.add_argument('-max-keep-day' , metavar='INT', dest='max_keep_days',
            default=360, type=int, required=False,
            help='The age of the cached result to be kept, (default: 360)')
    parser.add_argument('-v', dest='verbose', nargs='?', type=int, default=0, const=1, 
            help='show verbose information, (default: 0)')

    args = parser.parse_args()

    MAX_KEEP_DAYS = args.max_keep_days
    verbose=args.verbose

    print ("MAX_KEEP_DAYS = %d\n"%MAX_KEEP_DAYS)
    rtvalue = CleanCachedResult(MAX_KEEP_DAYS)
    sys.exit(rtvalue)

