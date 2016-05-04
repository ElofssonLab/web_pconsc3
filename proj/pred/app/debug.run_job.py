#!/usr/bin/env python
# Description: run job
import os
import sys
import subprocess
import time
import myfunc
import glob
from datetime import datetime
progname =  os.path.basename(sys.argv[0])
wspace = ''.join([" "]*len(progname))
rundir = os.path.dirname(os.path.realpath(__file__))

blastdir = "%s/%s"%(rundir, "soft/topcons2_webserver/tools/blast-2.2.26")
os.environ['BLASTMAT'] = "%s/data"%(blastdir)
os.environ['BLASTBIN'] = "%s/bin"%(blastdir)
os.environ['BLASTDB'] = "%s/%s"%(rundir, "soft/topcons2_webserver/database/blast/")
blastdb = "%s/%s"%(os.environ['BLASTDB'], "uniref90.fasta" )
runscript = "%s/%s"%(rundir, "soft/topcons2_webserver/workflow/pfam_workflow.py")

contact_email = "nanjiang.shu@scilifelab.se"

# note that here the url should be without http://

usage_short="""
Usage: %s seqfile_in_fasta -jobid JOBID -outpath DIR -tmpdir DIR -email EMAIL -baseurl BASE_WWW_URL
"""%(progname)

usage_ext="""
Description:
    run job

OPTIONS:
  -h, --help    Print this help message and exit

Created 2015-02-05, updated 2015-02-05, Nanjiang Shu
"""
usage_exp="""
Examples:
    %s /data3/tmp/tmp_dkgSD/query.fa -outpath /data3/result/rst_mXLDGD -tmpdir /data3/tmp/tmp_dkgSD
"""%(progname)

def PrintHelp(fpout=sys.stdout):#{{{
    print >> fpout, usage_short
    print >> fpout, usage_ext
    print >> fpout, usage_exp#}}}

def Sendmail(from_email, to_email, subject, bodytext):#{{{
    sendmail_location = "/usr/sbin/sendmail" # sendmail location
    p = os.popen("%s -t" % sendmail_location, "w")
    p.write("From: %s\n" % from_email)
    p.write("To: %s\n" % to_email)
    p.write("Subject: %s\n"%(subject))
    p.write("\n") # blank line separating headers from body
    p.write(bodytext)
    status = p.close()
    if status != 0:
        print "Sendmail to %s failed with status"%(to_email), status
    else:
        print "Sendmail to %s succeeded"%(to_email)
    return status

#}}}
def WriteTextResultFile(outfile, maplist, runtime_in_sec):#{{{
    try:
        outpath_result = os.path.dirname(outfile)
        methodlist = ['TOPCONS', 'OCTOPUS', 'Philius', 'PolyPhobius', 'SCAMPI', 'SPOCTOPUS']
        fpout = open(outfile, "w")
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print >> fpout, "##############################################################################"
        print >> fpout, "TOPCONS2 result file"
        print >> fpout, "Generated from http://%s at %s"%(g_params['base_www_url'], date)
        print >> fpout, "Total request time: %.1f seconds."%(runtime_in_sec)
        print >> fpout, "##############################################################################"
        cnt = 0
        for line in maplist:
            strs = line.split('\t')
            subfoldername = strs[0]
            length = int(strs[1])
            desp = strs[2]
            seq = strs[3]
            print >> fpout, "Sequence number: %d"%(cnt+1)
            print >> fpout, "Sequence name: %s"%(desp)
            print >> fpout, "Sequence length: %d aa."%(length)
            print >> fpout, "Sequence:\n%s\n\n"%(seq)

            for i in xrange(len(methodlist)):
                method = methodlist[i]
                if method == "TOPCONS":
                    topfile = "%s/%s/%s/topcons.top"%(outpath_result, subfoldername, "Topcons")
                elif method == "Philius":
                    topfile = "%s/%s/%s/query.top"%(outpath_result, subfoldername, "philius")
                elif method == "SCAMPI":
                    topfile = "%s/%s/%s/query.top"%(outpath_result, subfoldername, method+"_MSA")
                else:
                    topfile = "%s/%s/%s/query.top"%(outpath_result, subfoldername, method)
                if os.path.exists(topfile):
                    top = myfunc.ReadFile(topfile)
                else:
                    top = ""
                if top == "":
                    top = "***No topology could be produced with this method topfile=%s***"%(topfile)

                print >> fpout, "%s predicted topology:\n%s\n\n"%(method, top)


            dgfile = "%s/%s/dg.txt"%(outpath_result, subfoldername)
            dg_content = myfunc.ReadFile(dgfile)
            lines = dg_content.split("\n")
            dglines = []
            for line in lines:
                if line and line[0].isdigit():
                    dglines.append(line)
            if len(dglines)>0:
                print >> fpout,  "\nPredicted Delta-G-values (kcal/mol) "\
                        "(left column=sequence position; right column=Delta-G)\n"
                print >> fpout, "\n".join(dglines)

            reliability_file = "%s/%s/Topcons/reliability.txt"%(outpath_result, subfoldername)
            reliability = myfunc.ReadFile(reliability_file)
            if reliability != "":
                print >> fpout, "\nPredicted TOPCONS reliability (left "\
                        "column=sequence position; right column=reliability)\n"
                print >> fpout, reliability
            print >> fpout, "##############################################################################"
            cnt += 1



    except IOError:
        print "Failed to write to file %s"%(outfile)
#}}}
def RunJob(infile, outpath, tmpdir, email, jobid, g_params):#{{{
    rootname = os.path.basename(os.path.splitext(infile)[0])
    starttagfile   = "%s/runjob.start"%(outpath)
    runjob_errfile = "%s/runjob.err"%(outpath)
    runjob_logfile = "%s/runjob.log"%(outpath)
    finishtagfile = "%s/runjob.finish"%(outpath)
    rmsg = ""


    resultpathname = jobid

    outpath_result = "%s/%s"%(outpath, resultpathname)
    tarball = "%s.tar.gz"%(resultpathname)
    zipfile = "%s.zip"%(resultpathname)
    tarball_fullpath = "%s.tar.gz"%(outpath_result)
    zipfile_fullpath = "%s.zip"%(outpath_result)
    outfile = "%s/%s/Topcons/topcons.top"%(outpath_result, "seq_%d"%(0))
    resultfile_text = "%s/%s"%(outpath_result, "query.result.txt")

    tmp_outpath_result = "%s/%s"%(tmpdir, resultpathname)
    isOK = True
    try:
        os.makedirs(tmp_outpath_result)
        isOK = True
    except OSError:
        msg = "Failed to create folder %s"%(tmp_outpath_result)
        myfunc.WriteFile(msg+"\n", runjob_errfile, "a")
        isOK = False

    print "isOK =", isOK

    if isOK:
        tmp_mapfile = "%s/seqid_index_map.txt"%(tmp_outpath_result)

        maplist = []
        maplist_simple = []
        hdl = myfunc.ReadFastaByBlock(infile, method_seqid=0, method_seq=0)
        if hdl.failure:
            isOK = False
        else:
            recordList = hdl.readseq()
            cnt = 0
            while recordList != None:
                for rd in recordList:
                    maplist.append("%s\t%d\t%s\t%s"%("seq_%d"%cnt, len(rd.seq),
                        rd.description, rd.seq))
                    maplist_simple.append("%s\t%d\t%s"%("seq_%d"%cnt, len(rd.seq),
                        rd.description))
                    cnt += 1
                recordList = hdl.readseq()
            hdl.close()
        myfunc.WriteFile("\n".join(maplist_simple), tmp_mapfile)

        if isOK:
#             g_params['runjob_log'].append("tmpdir = %s"%(tmpdir))
            #cmd = [script_getseqlen, infile, "-o", tmp_outfile , "-printid"]
            datetime = time.strftime("%Y-%m-%d %H:%M:%S")
            rt_msg = myfunc.WriteFile(datetime, starttagfile)
            if rt_msg:
                g_params['runjob_err'].append(rt_msg)

            cmd = [runscript, infile,  tmp_outpath_result, blastdir, blastdb ]
            g_params['runjob_log'].append(" ".join(cmd))
            begin_time = time.time()
            try:
                rmsg = subprocess.check_output(cmd)
            except subprocess.CalledProcessError, e:
                g_params['runjob_err'].append(str(e)+"\n")
                g_params['runjob_err'].append(rmsg + "\n")
                suqoutfilelist = glob.glob("%s/*.sh.*.out"%(tmpdir))
                if len(suqoutfilelist)>0:
                    suqoutfile = suqoutfilelist[0]
                g_params['runjob_err'].append(myfunc.ReadFile(suqoutfile))
            end_time = time.time()
            runtime_in_sec = end_time - begin_time

            if os.path.exists(tmp_outpath_result):
                cmd = ["cp","-rf", tmp_outpath_result, outpath]
                try:
                    subprocess.check_output(cmd)
                except subprocess.CalledProcessError, e:
                    g_params['runjob_err'].append(str(e))

            if len(g_params['runjob_log']) > 0 :
                rt_msg = myfunc.WriteFile("\n".join(g_params['runjob_log']), runjob_logfile, "a")
                if rt_msg:
                    g_params['runjob_err'].append(rt_msg)

            datetime = time.strftime("%Y-%m-%d %H:%M:%S")
            if os.path.exists(outfile):
                rt_msg = myfunc.WriteFile(datetime, finishtagfile)
                if rt_msg:
                    g_params['runjob_err'].append(rt_msg)

# now write the text output to a single file
            WriteTextResultFile(resultfile_text, maplist, runtime_in_sec)

            # now making zip instead (for windows users)
            pwd = os.getcwd()
            os.chdir(outpath)
#             cmd = ["tar", "-czf", tarball, resultpathname]
            cmd = ["zip", "-rq", zipfile, resultpathname]
            try:
                subprocess.check_output(cmd)
            except subprocess.CalledProcessError, e:
                g_params['runjob_err'].append(str(e))
            os.chdir(pwd)

    isSuccess = False
    if (os.path.exists(finishtagfile) and os.path.exists(zipfile_fullpath)):
        isSuccess = True
    else:
        isSuccess = False
        failtagfile = "%s/runjob.failed"%(outpath)
        datetime = time.strftime("%Y-%m-%d %H:%M:%S")
        rt_msg = myfunc.WriteFile(datetime, failtagfile)
        if rt_msg:
            g_params['runjob_err'].append(rt_msg)

# send the result to email
    if myfunc.IsValidEmailAddress(email):
        from_email = "info@topcons.net"
        to_email = email
        subject = "Your result for TOPCONS2 JOBID=%s"%(jobid)
        if isSuccess:
            bodytext = """
Your result is ready at %s/pred/result/%s

Thanks for using TOPCONS2

        """%(g_params['base_www_url'], jobid)
        else:
            bodytext="""
We are sorry that your job with jobid %s is failed.

Please contact %s if you have any questions.

Attached below is the error message:
%s
            """%(jobid, contact_email, "\n".join(g_params['runjob_err']))
        g_params['runjob_log'].append("Sendmail %s -> %s, %s"% (from_email, to_email, subject)) #debug
        rtValue = Sendmail(from_email, to_email, subject, bodytext)
        if rtValue != 0:
            g_params['runjob_err'].append("Sendmail to %s failed with status %d"%(to_email, rtValue))

    if len(g_params['runjob_err']) > 0:
        rt_msg = myfunc.WriteFile("\n".join(g_params['runjob_err']), runjob_errfile, "w")
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

    return RunJob(infile, outpath, tmpdir, email, jobid, g_params)

#}}}

def InitGlobalParameter():#{{{
    g_params = {}
    g_params['isQuiet'] = True
    g_params['runjob_log'] = []
    g_params['runjob_err'] = []
    g_params['base_www_url'] = ""
    return g_params
#}}}
if __name__ == '__main__' :
    g_params = InitGlobalParameter()
    sys.exit(main(g_params))
