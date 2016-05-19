# Web server for PconsC3

##Author
Nanjiang Shu

nanjiang.shu@scilifelab.se

## Installation

1. Install dependencies for the web-server

2. Install the virtual environments by 

    $ bash setup_virtualenv.sh

3. Create the django database db.sqlite3

4. Run 

    $ bash init.sh

    to initialize the working folder

5. In the folder `proj`, create a softlink of the setting script.

    For development version

        $ ln -s dev_settings.py settings.py

    For release version

        $ ln -s pro_settings.py settings.py

    Note: for the release version, you need to create a file with secret key
    and stored at `/etc/django_pro_secret_key.txt`

6.  On the computational node. run 
    
    $ virtualenv env --system-site-packages

    to make sure that python can use all other system-wide installed packages


