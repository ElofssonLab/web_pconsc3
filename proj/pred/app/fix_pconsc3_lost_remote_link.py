#/usr/bin/env python

import os
import sys
import hashlib
import myfunc

rundir = os.path.dirname(os.path.realpath(__file__))
basedir = os.path.realpath("%s/.."%(rundir)) # path of the application, i.e. pred/
nodefile = "%s/static/computenode.txt"%(basedir)
resultpath = "%s/static/result"%(basedir)
runjoblogfile = "%s/static/log/runjob_log.log"%(basedir)

node = myfunc.ReadFile(nodefile).split("\n")[0]
epochtime = 0.00
usage="""
usage: 
    %s pcosnc3-finished-2.txt runjoblogfile resultpath
"""%(sys.argv[0])


try:
    finishedfile=sys.argv[1]
except:
    print usage
    sys.exit(1)

content=open(finishedfile,"r").read()
lines=content.split("\n")

dt_finished={}
for line in lines:
    if line:
        strs=line.split("\t")
        remoteid=strs[0]
        seq=strs[1]
        seqanno=strs[2]
        md5_key = hashlib.md5(seq).hexdigest() 
        dt_finished[md5_key] = [remoteid, seqanno]

content=open(runjoblogfile,"r").read()
lines=content.split("\n")
for line in lines:
    if line:
        strs=line.split("\t")
        jobid = strs[0]
        rstdir="%s/%s"%(resultpath, jobid)
        seqfile="%s/%s"%(rstdir, "query.fa")
        (seqid, seqanno, seq) = myfunc.ReadSingleFasta(seqfile)
        md5_key = hashlib.md5(seq).hexdigest()
        remotequeueidx_file = "%s/remotequeue_seqindex.txt"%(rstdir)
        origIndex = 0
        if md5_key in dt_finished:
            (remoteid, seqanno) = dt_finished[md5_key]
            txt = "%d\t%s\t%s\t%s\t%s\t%f"%(origIndex, node, remoteid, seqanno, seq, epochtime)
            print remotequeueidx_file, txt
            myfunc.WriteFile(txt, remotequeueidx_file, "w", True)
            os.system("chown apache:apache %s"%(remotequeueidx_file))



