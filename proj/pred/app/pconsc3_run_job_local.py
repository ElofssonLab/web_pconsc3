#!/usr/bin/env python
# Description: run job in the local machine
#              the whole input sequence file as input to the program, do not
#              split

import os
import sys
import subprocess
import time
import myfunc
import glob
import hashlib
import shutil

DEBUG = True

progname =  os.path.basename(sys.argv[0])
wspace = ''.join([" "]*len(progname))
rundir = os.path.dirname(os.path.realpath(__file__))
suq_basedir = "/tmp"
if os.path.exists("/scratch"):
    suq_basedir = "/scratch"
elif os.path.exists("/tmp"):
    suq_basedir = "/tmp"

runscript = "%s/%s"%(rundir, "soft/pconsc3/run_pconsc3_nj.sh")

basedir = os.path.realpath("%s/.."%(rundir)) # path of the application, i.e. pred/

contact_email = "nanjiang.shu@scilifelab.se"
vip_user_list = [
        "nanjiang.shu@scilifelab.se"
        ]

# note that here the url should be without http://

usage_short="""
Usage: %s seqfile_in_fasta 
       %s -jobid JOBID -outpath DIR -tmpdir DIR
       %s -email EMAIL -baseurl BASE_WWW_URL
"""%(progname, wspace, wspace)

usage_ext="""\
Description:
    run job in the local machine

OPTIONS:
  -h, --help    Print this help message and exit

Created 2015-02-05, updated 2015-05-27, Nanjiang Shu
"""
usage_exp="""
Examples:
    %s /data3/tmp/tmp_dkgSD/query.fa -outpath /data3/result/rst_mXLDGD -tmpdir /data3/tmp/tmp_dkgSD
"""%(progname)

def PrintHelp(fpout=sys.stdout):#{{{
    print >> fpout, usage_short
    print >> fpout, usage_ext
    print >> fpout, usage_exp#}}}

def WriteTextResultFile(outfile, outpath_result, maplist, runtime_in_sec, statfile=""):#{{{
    try:
        fpout = open(outfile, "w")

        fpstat = None
        numTMPro = 0

        if statfile != "":
            fpstat = open(statfile, "w")

        cnt = 0
        for line in maplist:
            strs = line.split('\t')
            subfoldername = strs[0]
            length = int(strs[1])
            desp = strs[2]
            seq = strs[3]
            isTMPro = False
            outpath_this_seq = "%s/%s"%(outpath_result, subfoldername)
            predfile = "%s/query.hhE0.pconsc3.out"%(outpath_this_seq)
            g_params['runjob_log'].append("predfile =  %s.\n"%(predfile))
            if not os.path.exists(predfile):
                g_params['runjob_log'].append("predfile %s does not exist\n"%(predfile))

            cnt += 1

        if fpstat:
            fpstat.close()
    except IOError:
        print "Failed to write to file %s"%(outfile)
#}}}
def RunJob(infile, outpath, tmpdir, email, jobid, g_params):#{{{
    all_begin_time = time.time()

    rootname = os.path.basename(os.path.splitext(infile)[0])
    starttagfile   = "%s/runjob.start"%(outpath)
    runjob_errfile = "%s/runjob.err"%(outpath)
    runjob_logfile = "%s/runjob.log"%(outpath)
    finishtagfile = "%s/runjob.finish"%(outpath)

    rmsg = ""

    resultpathname = jobid

    outpath_result = "%s/%s"%(outpath, resultpathname)
    tmp_outpath_result = "%s/%s"%(tmpdir, resultpathname)
    zipfile = "%s.zip"%(resultpathname)
    zipfile_fullpath = "%s.zip"%(outpath_result)
    seqlength = myfunc.GetSingleFastaLength(infile)

    datetime = time.strftime("%Y-%m-%d %H:%M:%S")
    rt_msg = myfunc.WriteFile(datetime, starttagfile)

    cmd = [runscript, infile, tmp_outpath_result]
    g_params['runjob_log'].append(" ".join(cmd))
    cmdline = " ".join(cmd)
    begin_time = time.time()
    print "app cmdline: %s"%(cmdline)
    try:
        rmsg = subprocess.check_output(cmd)
        g_params['runjob_log'].append("workflow:\n"+rmsg+"\n")
    except subprocess.CalledProcessError, e:
        g_params['runjob_err'].append(str(e)+"\n")
        g_params['runjob_err'].append(rmsg + "\n")
        pass

    end_time = time.time()
    runtime_in_sec = end_time - begin_time
    timefile = "%s/time.txt"%(tmp_outpath_result)
    content = "%s\t%d\t%f"%(jobid, seqlength, runtime_in_sec)
    myfunc.WriteFile(content, timefile, "w")

    if os.path.exists(tmp_outpath_result):
        cmd = ["mv","-f", tmp_outpath_result, outpath_result]
        isCmdSuccess = False
        try:
            subprocess.check_output(cmd)
            isCmdSuccess = True
        except subprocess.CalledProcessError, e:
            g_params['runjob_err'].append(str(e)+"\n")
            pass


    datetime = time.strftime("%Y-%m-%d %H:%M:%S")
    rt_msg = myfunc.WriteFile(datetime, finishtagfile)
    if rt_msg:
        g_params['runjob_err'].append(rt_msg)

    os.chdir(outpath)
    cmd = ["zip", "-rq", zipfile, resultpathname]
    try:
        subprocess.check_output(cmd)
    except subprocess.CalledProcessError, e:
        g_params['runjob_err'].append(str(e))
        pass

    isSuccess = False
    if (os.path.exists(finishtagfile) and os.path.exists(zipfile_fullpath)):
        isSuccess = True
        shutil.rmtree(tmpdir)
    else:
        isSuccess = False
        failtagfile = "%s/runjob.failed"%(outpath)
        datetime = time.strftime("%Y-%m-%d %H:%M:%S")
        rt_msg = myfunc.WriteFile(datetime, failtagfile)
        if rt_msg:
            g_params['runjob_err'].append(rt_msg)

    if len(g_params['runjob_log']) > 0:
        rt_msg = myfunc.WriteFile("\n".join(g_params['runjob_log'])+"\n", runjob_logfile, "w")
        return 1
    if len(g_params['runjob_err']) > 0:
        rt_msg = myfunc.WriteFile("\n".join(g_params['runjob_err'])+"\n", runjob_errfile, "w")
        return 1
    return 0
#}}}
def main(g_params):#{{{
    argv = sys.argv
    numArgv = len(argv)
    if numArgv < 2:
        PrintHelp()
        return 1

    outpath = ""
    infile = ""
    tmpdir = ""
    email = ""
    jobid = ""

    i = 1
    isNonOptionArg=False
    while i < numArgv:
        if isNonOptionArg == True:
            infile = argv[i]
            isNonOptionArg = False
            i += 1
        elif argv[i] == "--":
            isNonOptionArg = True
            i += 1
        elif argv[i][0] == "-":
            if argv[i] in ["-h", "--help"]:
                PrintHelp()
                return 1
            elif argv[i] in ["-outpath", "--outpath"]:
                (outpath, i) = myfunc.my_getopt_str(argv, i)
            elif argv[i] in ["-tmpdir", "--tmpdir"] :
                (tmpdir, i) = myfunc.my_getopt_str(argv, i)
            elif argv[i] in ["-jobid", "--jobid"] :
                (jobid, i) = myfunc.my_getopt_str(argv, i)
            elif argv[i] in ["-baseurl", "--baseurl"] :
                (g_params['base_www_url'], i) = myfunc.my_getopt_str(argv, i)
            elif argv[i] in ["-email", "--email"] :
                (email, i) = myfunc.my_getopt_str(argv, i)
            elif argv[i] in ["-q", "--q"]:
                g_params['isQuiet'] = True
                i += 1
            elif argv[i] in ["-force", "--force"]:
                g_params['isForceRun'] = True
                i += 1
            else:
                print >> sys.stderr, "Error! Wrong argument:", argv[i]
                return 1
        else:
            infile = argv[i]
            i += 1

    if jobid == "":
        print >> sys.stderr, "%s: jobid not set. exit"%(sys.argv[0])
        return 1

    if myfunc.checkfile(infile, "infile") != 0:
        return 1
    if outpath == "":
        print >> sys.stderr, "outpath not set. exit"
        return 1
    elif not os.path.exists(outpath):
        try:
            subprocess.check_output(["mkdir", "-p", outpath])
        except subprocess.CalledProcessError, e:
            print >> sys.stderr, e
            return 1
    if tmpdir == "":
        print >> sys.stderr, "tmpdir not set. exit"
        return 1
    elif not os.path.exists(tmpdir):
        try:
            subprocess.check_output(["mkdir", "-p", tmpdir])
        except subprocess.CalledProcessError, e:
            print >> sys.stderr, e
            return 1

    numseq = myfunc.CountFastaSeq(infile)
    g_params['debugfile'] = "%s/debug.log"%(outpath)
    return RunJob(infile, outpath, tmpdir, email, jobid, g_params)

#}}}

def InitGlobalParameter():#{{{
    g_params = {}
    g_params['isQuiet'] = True
    g_params['runjob_log'] = []
    g_params['runjob_err'] = []
    g_params['isForceRun'] = False
    g_params['base_www_url'] = ""
    return g_params
#}}}
if __name__ == '__main__' :
    g_params = InitGlobalParameter()
    sys.exit(main(g_params))
