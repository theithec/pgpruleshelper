# pgpruleshelper
* **Update** rules in [enigmails](https://addons.mozilla.org/de/thunderbird/addon/enigmail/ ) pgprules.xml from a file of the same format
* **Export**  rules from enigmails pgprules.xml into a file of the same format
	

## Requirements 
From version 0.4 and on python2 >= 2.5 or python3 >= 3.4 (older 3's not tested) is required.
 
For older versions is python2 >=2.4 is required. Older python versions _may_ work. 

python-tk/python3-tk is required for the gui.


## Install
Save the file 'pgpruleshelper.py' somewhere you remember and make it executable


## Import
Of course you need a import-file someone created, like 'my\_encrypted\_mailinglist\_update.xml' or 'my\_many\_encrypted\_mailinglists\_updates.xml'

* use "open with" and point to the pgpruleshelper.py.
* select the rules to import (even its only one) and confirm.


## Export
* call 'pgpruleshelper -E' in a command line interpreter 
* select the rules to export (even its only one) and confirm.
* save


## Options
There are more command line options. See "pgpruleshelper.py --help"


## Note
This script does not edit or read your OpenPGP keys in any way.
You have to import (and trust) keys yourself.  
You just don't have to manually edit the rules in Thunderbird.

Some messages (still) have no (or bad) english translation.

### Linux ###
In a few distros python-tk is not preinstalled. 

### Windows ###
You may not see the 'pgpruleshelper.py' in the 'open with'-dialog.
Choose the right directory and type 'pgpruleshelper.py' yourself.

### Mac ###
You need a wrapper app from Automator or such to select in 'open-with'-dialog (i think)

## kpgpruleshelper (for kmail)
* **Update** encryption settings for contacts managed by akonadi from a pgprules.xml (very basic).






