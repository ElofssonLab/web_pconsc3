#!/usr/bin/perl -w
# get set suq ntask
#Created 2015-03-20, updated 2015-03-20, Nanjiang Shu
use CGI qw(:standard);
use CGI qw(:cgi-lib);
use CGI qw(:upload);

use Cwd 'abs_path';
use File::Basename;
my $rundir = dirname(abs_path(__FILE__));
# at proj
my $basedir = "$rundir/../";
my $auth_ip_file = "$basedir/auth_iplist.txt";#ip address which allows to run cgi script

my $suq_exec = "/usr/bin/suq";

print header();
print start_html(-title => "get suq list",
    -author => "nanjiang.shu\@scilifelab.se",
    -meta   => {'keywords'=>''});

if(!param())
{
    print "<pre>\n";
    print "usage: curl get_suqlist.cgi -d base=suqbasedir \n\n";
    print "       or in the browser\n\n";
    print "       get_suqlist.cgi?base=suqbasedir\n\n";
    print "Example\n";
    print "       get_suqlist.cgi?base=log\n";
    print "</pre>\n";
    print end_html();
}
if(param())
{
    my $suqbase=param('base');
    my $remote_host = $ENV{'REMOTE_ADDR'};
    $suqbase = "$basedir/pred/static/$suqbase";

    my @auth_iplist = ();
    open(IN, "<", $auth_ip_file) or die;
    while(<IN>) {
        chomp;
        push @auth_iplist, $_;
    }
    close IN;

    if (grep { $_ eq $remote_host } @auth_iplist) {
        $suqlist = `$suq_exec -b $suqbase ls`;
        print "<pre>";
        print "Host IP: $remote_host\n\n";
        print "Suq list:\n\n";
        print "$suqlist\n";

        print "</pre>";
    }else{
        print "Permission denied!\n";
    }

    print '<br>';
    print end_html();
}

