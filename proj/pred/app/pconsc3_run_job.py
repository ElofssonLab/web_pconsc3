#!/usr/bin/env python
# Description: run job

# Derived from topcons2_workflow_run_job.py on 2015-05-27
# how to create md5
# import hashlib
# md5_key = hashlib.md5(string).hexdigest()
# subfolder = md5_key[:2]

# 

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

runscript = "%s/%s"%(rundir, "soft/pconsc3/run_pconsc3.sh")
#script_scampi = "%s/%s"%(rundir, "mySCAMPI_run.pl")

basedir = os.path.realpath("%s/.."%(rundir)) # path of the application, i.e. pred/
path_md5cache = "%s/static/md5"%(basedir)
path_cache = "%s/static/result/cache"%(basedir)

contact_email = "nanjiang.shu@scilifelab.se"
vip_user_list = [
        "nanjiang.shu@scilifelab.se"
        ]

# note that here the url should be without http://

usage_short="""
Usage: %s seqfile_in_fasta 
       %s -jobid JOBID -outpath DIR -tmpdir DIR
       %s -email EMAIL -baseurl BASE_WWW_URL
       %s [-force]
"""%(progname, wspace, wspace, wspace)

usage_ext="""\
Description:
    run job

OPTIONS:
  -force        Do not use cahced result
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
    split_seq_dir = "%s/splitaa"%(outpath)
    init_torun_idx_file = "%s/init_torun_seqindex.txt"%(outpath)# ordered seq index to run
    cached_not_finish_idx_file = "%s/cached_not_finish_seqindex.txt"%(outpath)

# note: init_torun_seqindex.txt is created when the job is submitted
#       torun_seqindex.txt is created later by the queue daemon
#       torun_seqindex should be a subset of init_torun_seqindex

    rmsg = ""


    resultpathname = jobid

    outpath_result = "%s/%s"%(outpath, resultpathname)
    tarball = "%s.tar.gz"%(resultpathname)
    zipfile = "%s.zip"%(resultpathname)
    tarball_fullpath = "%s.tar.gz"%(outpath_result)
    zipfile_fullpath = "%s.zip"%(outpath_result)
    mapfile = "%s/seqid_index_map.txt"%(outpath_result)
    finished_seq_file = "%s/finished_seqs.txt"%(outpath_result)

    isFinished = False

    try:
        os.makedirs(outpath_result)
        isOK = True
    except OSError:
        msg = "Failed to create folder %s"%(outpath_result)
        myfunc.WriteFile(msg+"\n", runjob_errfile, "a")
        isOK = False
        pass


    if isOK:
        try:
            open(finished_seq_file, 'w').close()
        except:
            pass
#first getting result from caches
# ==================================

        maplist = []
        maplist_simple = []
        toRunDict = {}
        cachedNotFinishIndexList = []
        cntFinished = 0
        numseq = 0
        hdl = myfunc.ReadFastaByBlock(infile, method_seqid=0, method_seq=0)
        if hdl.failure:
            isOK = False
        else:
            datetime = time.strftime("%Y-%m-%d %H:%M:%S")
            rt_msg = myfunc.WriteFile(datetime, starttagfile)

            recordList = hdl.readseq()
            cnt = 0
            origpath = os.getcwd()
            while recordList != None:
                for rd in recordList:
                    isSkip = False
                    outpath_this_seq = "%s/%s"%(outpath_result, "seq_%d"%cnt)
                    subfoldername_this_seq = "seq_%d"%(cnt)

                    maplist.append("%s\t%d\t%s\t%s"%("seq_%d"%cnt, len(rd.seq),
                        rd.description, rd.seq))
                    maplist_simple.append("%s\t%d\t%s"%("seq_%d"%cnt, len(rd.seq),
                        rd.description))
                    if not g_params['isForceRun']:
                        md5_key = hashlib.md5(rd.seq).hexdigest()
                        subfoldername = md5_key[:2]
                        md5_link = "%s/%s/%s"%(path_md5cache, subfoldername, md5_key)
                        if DEBUG:
                            g_params['runjob_log'].append("md5_link {}\n".format(md5_link))

                        if os.path.exists(md5_link):
                            # create a symlink to the cache
                            rela_path = os.path.relpath(md5_link, outpath_result) #relative path
                            os.chdir(outpath_result)
                            os.symlink(rela_path, subfoldername_this_seq)

                            resultfile = "%s/query.fa.hhE0.pconsc3.out"%(outpath_this_seq)
                            thisseqfile = "%s/query.fa"%(outpath_this_seq)

                            if os.path.exists(outpath_this_seq):
                                isSkip = True
                                if  os.path.exists(resultfile):
                                    runtime = 0.0 #in seconds
                                    info_finish = [ "seq_%d"%cnt,
                                            str(len(rd.seq)), "cached", str(runtime),
                                            rd.description]
                                    myfunc.WriteFile("\t".join(info_finish)+"\n",
                                            finished_seq_file, "a", isFlush=True)
                                    cntFinished += 1
                                else:
                                    cachedNotFinishIndexList.append(str(cnt))


                    if not isSkip:
                        # first try to delete the outfolder if exists
                        if os.path.exists(outpath_this_seq):
                            try:
                                shutil.rmtree(outpath_this_seq)
                            except OSError:
                                pass
                        origIndex = cnt
                        svalue = 0 # sorting value, not applied in this script
                        toRunDict[origIndex] = [rd.seq, svalue, rd.description]

                    cnt += 1
                recordList = hdl.readseq()
            hdl.close()
            numseq = cnt
        myfunc.WriteFile("\n".join(maplist_simple)+"\n", mapfile)

        if DEBUG:
            g_params['runjob_log'].append("toRunDict: {}\n".format(toRunDict))

        sortedlist = sorted(toRunDict.items(), key=lambda x:x[1][1], reverse=True)
        #format of sortedlist [(origIndex: [seq, svalue, description]), ...]
        torun_str_list = []
        for item in sortedlist:
            origIndex = item[0]
            torun_str_list.append(str(origIndex))

        myfunc.WriteFile("\n".join(torun_str_list)+"\n", init_torun_idx_file)
        myfunc.WriteFile("\n".join(cachedNotFinishIndexList)+"\n", cached_not_finish_idx_file)

        if len(torun_str_list) > 0 and not os.path.exists(split_seq_dir):
            os.makedirs(split_seq_dir)

        # create cache for the rest of sequences
        for item in sortedlist:
            if DEBUG:
                g_params['runjob_log'].append("create cache for item: {}\n".format(item))
            origIndex = item[0]
            seq = item[1][0]
            description = item[1][2]

            seqfile_this_seq = "%s/%s"%(split_seq_dir, "query_%d.fa"%(origIndex))
            seqcontent = ">%s\n%s\n"%(description, seq)
            myfunc.WriteFile(seqcontent, seqfile_this_seq, "w", True)


        all_end_time = time.time()
        all_runtime_in_sec = all_end_time - all_begin_time

        if cntFinished == numseq:
            isFinished = True

        if isFinished:
            datetime = time.strftime("%Y-%m-%d %H:%M:%S")
            if os.path.exists(finished_seq_file):
                rt_msg = myfunc.WriteFile(datetime, finishtagfile)
                if rt_msg:
                    g_params['runjob_err'].append(rt_msg)

# now write the text output to a single file
            statfile = "%s/%s"%(outpath_result, "stat.txt")
            dumped_resultfile = "%s/%s"%(outpath_result, "query.pconsc3.txt")
            WriteTextResultFile(dumped_resultfile, outpath_result, maplist,
                    all_runtime_in_sec, statfile=statfile)

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
                # delete the tmpdir if succeeded
                shutil.rmtree(tmpdir)
            else:
                isSuccess = False
                failtagfile = "%s/runjob.failed"%(outpath)
                datetime = time.strftime("%Y-%m-%d %H:%M:%S")
                rt_msg = myfunc.WriteFile(datetime, failtagfile)
                if rt_msg:
                    g_params['runjob_err'].append(rt_msg)

# send the result to email
# do not sendmail at the cloud VM
            if (g_params['base_www_url'].find("topcons.net") != -1 and
                    myfunc.IsValidEmailAddress(email)):
                from_email = "info@pconsc3.bioinfo.se"
                to_email = email
                subject = "Your result for PconsC3 JOBID=%s"%(jobid)
                if isSuccess:
                    bodytext = """
Your result is ready at %s/pred/result/%s

Thanks for using PconsC3
                """%(g_params['base_www_url'], jobid)
                else:
                    bodytext="""
We are sorry that your job with jobid %s is failed.

Please contact %s if you have any questions.

Attached below is the error message:
%s
                    """%(jobid, contact_email, "\n".join(g_params['runjob_err']))

                g_params['runjob_log'].append("Sendmail %s -> %s, %s"% (from_email, to_email, subject)) #debug
                rtValue = myfunc.Sendmail(from_email, to_email, subject, bodytext)
                if rtValue != 0:
                    g_params['runjob_err'].append("Sendmail to {} failed with status {}".format(to_email, rtValue))

    if len(g_params['runjob_log']) > 0:
        rt_msg = myfunc.WriteFile("\n".join(g_params['runjob_log'])+"\n", runjob_logfile, "w")
        return 1
    if len(g_params['runjob_err']) > 0:
        rt_msg = myfunc.WriteFile("\n".join(g_params['runjob_err'])+"\n", runjob_errfile, "w")
        return 1
    if os.path.exits(tmpdir):
        shutil.rmtree(tmpdir)
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
    if not os.path.exists(path_cache):
        os.makedirs(path_cache)
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
