#! /usr/bin/env python
# -*- coding: utf-8 -*-

u'''
pgpruleshelper.py [options] [pfad/zur/source.xml] [email1 email2 ...]

Update/Export der Empfängerregeln von enigmails Regeln in der pgprules.xml
für auswählbare Adressen aus einer Datei gleichen Formats.
Bei Update wird eine Kopie mit Timestamp erstellt

1. Die Source-Datei (die mit den Updates)
a) wird im GUI-Modus(default) abgefragt, wenn keine Argumente vorhanden sind
b) ist das erste Argument (wird auch im "öffnen mit"-Dialog übergeben)
c) wenn die Export-Option gewählt ist und keine Argumente vorhanden sind,
   gilt 3)a-b

2. Die E-Mail-Adressen,deren Regeln geändert  werden,
a) der Parameter der Email-Option (als kommaseperierte Liste)
b) durch die Option -a oder --all alle Regeln aus der Source-Datei
c) werden sonst  im Gui-Modus abgefragt

3. Die Target-Datei
a) ist die pgprules.xml  aus dem einzigen oder dem als 'Default'
   gekennzeichneten Thunderbird-Profil-Ordner
b) ist die pgprules.xml aus dem durch die Profil-Option ausgewählten
   Thunderbird-Profil-Ordner
c) der Parameter der Export-Option; ist der Parameter ein leerer String ("")
   wird sie im GUI-Modus per Dialog abgefragt, im CLi-Modus wird das erzeugte
   XML ausgegeben, Kurzform für -e "" ist -E

pgpruleshelper.py --help zeigt Optionen
'''


import ConfigParser
import codecs
import datetime
import optparse
import os
import shutil
import sys
import time
from xml.dom import minidom

import locale


__version__ = '0.3.3'
'''
a little bit l18n

'0.3.2'
fixed missing rules-validation (indentation-err)

'0.3.1'
changes:
vor dem Erstellen der Sicherheitskopie wird geprüft, ob das Orginal überhaupt
existiert.
Dadurch kein Crash bei nicht-existenter Datei.

0.3
...

'''

### l18n
# deployment should be as simpel as possible
# so all has to be in one file - including base translation
#
defl = locale.getdefaultlocale()

LANG_ID = 1
if defl[0].lower().startswith('de'):
    LANG_ID = 0
#key=en , de=0, [en=1]

T = {
    u'export': (u'exportieren',),

    u'update': (u'aktualisieren',),

    u'successhint':
        (u'''\nBitte Thunderbird neu starten - \n
außer du bist dir sicher, dass seit dem Start von Thunderbird
keine Empfängerregeln benutzt oder
der Empfängerregeln-Dialog aufgerufen wurde.
(Beachte, dass Thunderbird u.U. automatisch im Hintergrund gestartet wurde).

Bei Problemen die entsprechende Regel löschen,
Thunderbird ganz beenden & neu starten,
die Regel als allererstes neu importieren.
''',
    u'''\nPlease restart thunderbird  - \n
außer du bist dir sicher, dass seit dem Start von Thunderbird
keine Empfängerregeln benutzt oder
der Empfängerregeln-Dialog aufgerufen wurde.
(Beachte, dass Thunderbird u.U. automatisch im Hintergrund gestartet wurde).

Bei Problemen die entsprechende Regel löschen,
Thunderbird ganz beenden & neu starten,
die Regel als allererstes neu importieren.
'''),

    u'longtitle':
        (u'%s der Empfängerregeln (v.%s)',
         u'%s pgprules (v.%s)'),

    u'successmsg': (
        u'%s soweit erfolgreich.',
        u'%s ok',
    ),

    u'no rule for': (u"Keine Regel für %s",),

    u'no rules given': (u"Keine Regeln angegeben",),

    u'failed': (u"%s der Empfängerregeln NICHT erfolgreich!",
                u'%s FAILED!'),

    u'no source file given': (u"Keine Source-Datei angegeben"),

    u'invalid file': (u"Ungültige Datei",),

    u'open file with rules': (u'Datei mit Regeln öffnen',),

    u'choose rules': (u'Für welche Adressen die Regeln %s?',
                      u'choose rules for %s',
                      ),

    u'create file?': (u'Datei %s erstellen?',)
}


def _(key):
    try:
        return T[key][LANG_ID]
    except (KeyError, IndexError):
        return key


### xml

try:
    from xml.parsers.expat import ExpatError as ParseError
except ImportError:  # py2.2+-?
    from xml.sax._exceptions import SAXParseException as ParseError


def mailval(rule):
    return rule.attributes['email'].value[1:-1]


def rule_for_mail(rulelist, email):
    for rule in rulelist.getElementsByTagName('pgpRule'):
        rule_email = mailval(rule)
        if email == rule_email:
            return rule


def update_rulelist(target_rulelist, rules):
    for rule in rules:
        email = mailval(rule)
        # keyIDs to upper - without not "0x"-prefix
        v = rule.attributes['keyId'].value
        rule.attributes['keyId'].value = v.upper().replace('0X', '0x')

        oldrule = rule_for_mail(target_rulelist, email)
        root = target_rulelist.documentElement
        if oldrule:
            root.replaceChild(rule, oldrule)
        else:
            root.appendChild(rule)


def empty_rulelist():
    return minidom.parseString('<pgpRuleList></pgpRuleList>')


def write_rulelist(rulelist, filepath):
    rulelist.writexml(codecs.open(filepath, encoding='utf-8', mode='w+'))


### thunderbird:
def get_tb_dir():
    if sys.platform.startswith('linux'):
        return os.path.join(os.environ['HOME'], '.thunderbird')
    elif sys.platform.startswith('win'):
        return os.path.join(os.environ['APPDATA'], 'Thunderbird')
    elif sys.platform.startswith('darwin'):
        return os.path.join(os.environ['HOME'], 'Library', 'Thunderbird')


def get_tb_profile_dir(tb_dir, profilename=None):
    pfile = os.path.join(tb_dir, 'profiles.ini')
    if not os.path.isfile(pfile):
        return

    cop = ConfigParser.ConfigParser()
    cop.read(pfile)
    sections = [s for s in cop.sections() if s.startswith('Profile')]

    is_default = lambda s: cop.has_option(s, 'Default') and cop.get(s,
                                                                'Default')
    is_name = lambda s: cop.get(s, 'Name') == profilename
    is_wanted = {True: is_name, False: is_default}[bool(profilename)]

    for section in sections:
        if len(sections) == 1 or is_wanted(section):
            return os.path.join(tb_dir, cop.get(section, 'Path'))


### misc
def mk_timestamped_copy(fpath):
    if (os.path.exists(fpath)):
        ts = datetime.datetime.fromtimestamp(time.time()).strftime(
                                                    '%Y-%m-%d_%H%M%S')
        i = fpath.rfind('.')
        cpath = ''.join(fpath[:i] + ts + fpath[i:])
        shutil.copyfile(fpath, cpath)


### ui
class Export(object):
    def initMode(self):
        self.title = u'Export'
        self.action = _(u'export')

    def getSourcePathForMode(self):
        return self.tbRulelistpath()

    def getTargetPathForMode(self):
        return self.opts.exportpath or self.askForTargetPath()

    def getTargetForMode(self):
        if self.targetpath:
            return self.rulelistFromPath(self.targetpath)
        else:
            return empty_rulelist()

    def allowCreateForMode(self):
        return True


class Update(object):
    def initMode(self):
        self.title = u'Update'
        self.action = _(u'update')
        self.successhint = _(u'successhint')

    def getSourcePathForMode(self):
        return self.askForSourcePath()

    def getTargetPathForMode(self):
        p = self.tbRulelistpath()
        if p and self.opts.mk_cpy:
            mk_timestamped_copy(p)
        return p

    def getTargetForMode(self):
        return self.rulelistFromPath(self.targetpath)

    def allowCreateForMode(self):
        return self.askCreate()


class Ui(object):
    def __init__(self, args, opts):
        self.args = args
        self.opts = opts
        self.run_tests = False
        self.successhint = u''

    def start(self):
        self.longtitle = _(u'longtitle') % (self.title, __version__)
        self.source = self.getSource()
        rules = self.getSelectedRules()
        self.targetpath = self.getTargetPathForMode()
        target = self.getTargetForMode()
        update_rulelist(target, rules)
        if self.targetpath:
            self.writeRulelist(target)
            self.msg(self.successMsg())
        else:
            print target.toxml()

    def successMsg(self):
        return os.linesep.join(_('successmsg') % self.longtitle,
                               self.successhint)

    def getSource(self):
        try:
            spath = self.args[0]
        except IndexError:
            spath = self.getSourcePathForMode()
        return self.rulelistFromPath(spath, False)

    def getTargetPathForMode(self):
        return self.askForTargetPath()

    def askCreate(self):
        return self.opts.createtarget

    def getSelectedRules(self):
        rules = None
        if self.opts.importall:
            rules = self.source.getElementsByTagName('pgpRule')
        elif self.opts.emails:
            rules = []
            for email in self.opts.emails.split(','):
                email = email.strip()
                rule = rule_for_mail(self.source, email)
                if not rule:
                    self.err(_(u"no rule for %s") % email)
                else:
                    rules.append(rule)
        else:
            rules = self.askForRules()
        if not rules:
            self.err(_("no rules given"))
        return rules

    def rulelistFromPath(self, fpath, ask_create=True):
        try:
            xml = minidom.parse(fpath)
        except (IOError, AttributeError), e:
            if ask_create and self.allowCreateForMode():
                self.writeRulelist(empty_rulelist())
                return self.rulelistFromPath(fpath)
            self.err(_(u"invalid file") + u": %s\n(%s)" % (fpath, e))
        except ParseError, e:
            self.err(_(u"invalid xml file") + u": %s\n" % (fpath,) + str(e))
        if xml.documentElement.tagName != "pgpRuleList":
            self.err(_(u"file contains no rules %s") % fpath)
        return xml

    def tbRulelistpath(self):
        profile_dir = get_tb_profile_dir(
            self.opts.tbdirpath or get_tb_dir(),
            self.opts.profilename
        )
        if not profile_dir:
            self.err(_(u"no thunderbird profile found"))
        return os.path.join(profile_dir, 'pgprules.xml')

    def writeRulelist(self, rulelist):
        try:
            write_rulelist(rulelist, self.targetpath)
        except IOError, e:
            self.err(_("write error") + ": %s\n%s" % (self.targetpath, e))

    def err(self, text):
        self.errmsg = text
        self.msg(os.linesep.join((self.errmsg,  _(u"failed") % self.title)))
        if not self.run_tests:
            sys.exit(-1)
        else:
            raise Exception(self.errmsg)


class Cli(Ui):
    def askForSourcePath(self):
        self.err(_("no source file given"))

    def askForTargetPath(self):
        return None

    def askForRules(self):
        return None

    def msg(self, text):
        sys.stderr.write(text + os.linesep)


class Gui(Ui):
    def __init__(self, args, opts):
        from Tkinter import Tk, IntVar, Checkbutton, Label
        import tkFileDialog, tkSimpleDialog, tkMessageBox
        self.tk = Tk()
        if sys.version_info >= (2, 6):
            self.tk.withdraw()
        self.IntVar, self.checkbutton, self.label = IntVar, Checkbutton, Label
        self.fileDialog = tkFileDialog
        self.simpleDialog = tkSimpleDialog
        self.msgbox = tkMessageBox
        super(Gui, self).__init__(args, opts)

    def _get_filepath(self, dlg, title):
        fp = dlg(
            title=title,
            filetypes=(("XML-Dateien", "*.xml"),),
            initialdir=os.path.expanduser('~'),
        )
        if not fp:
            self.err(_(u"invalid file") + ": %s" % title)
        return fp

    def askForSourcePath(self):
        return self._get_filepath(self.fileDialog.askopenfilename,
                                  _(u"open file with rules"))

    def askForTargetPath(self):
        return self._get_filepath(
            self.fileDialog.asksaveasfilename,
            _(u"exportfile")
        )

    def askForRules(self):
        avail_rules = self.source.getElementsByTagName('pgpRule')
        selectedrules = {}
        intVar = self.IntVar
        checkbutton = self.checkbutton
        label = self.label
        modeaction = self.action

        class RuleChooserDialog(self.simpleDialog.Dialog):
            def body(self, master):
                cnt = 0
                l = label(master,
                          text=_(u'choose rules') %
                          modeaction)
                l.pack(anchor="w")
                l.grid(row=cnt)
                for rule in avail_rules:
                    cnt += 1
                    var = intVar()
                    c = checkbutton(master, text=mailval(rule),
                                    variable=var,
                                    justify="left")
                    c.grid(row=cnt, sticky="w")
                    selectedrules[rule] = var.get

            def apply(self):
                self.result = True

        if RuleChooserDialog(self.tk, title=self.longtitle).result:
            return [r for r in avail_rules if selectedrules[r]()]

    def askCreate(self):
        return super(Gui, self).askCreate() or \
           self.msgbox.askyesno(self.title,
                                _(u"create file?") % self.targetpath)

    def msg(self, text):
        self.msgbox.showinfo(self.longtitle, text)


def buildUi(args, opts, UiCls=None, ModeCls=None):
    if not UiCls:
        uiClzs = (Cli, Gui,)
        UiCls = uiClzs[int(opts.use_gui)]
    ui = UiCls(args, opts)

    if not ModeCls:
        modeClzs = (Export, Update)
        ModeCls = modeClzs[int(opts.exportpath is None)]

    ui.__class__ = type(
        "%s%s" % (ModeCls.__name__, UiCls.__name__),
        (ModeCls, UiCls), {}
    )
    ui.initMode()
    return ui


def get_optparser():

    oparser = optparse.OptionParser(__doc__)
    oparser.add_option('-e', '--export',
                       action="store", type="string", dest="exportpath",
                       help="""Export to given filepath.
If the  argument is an empty string, gui-mode asks for path,
cli-mode prints output""")
    oparser.add_option('-E',
                       action="store_const", const="", dest="exportpath",
                       help=u"""shortform for -e \"\"""")
    oparser.add_option('-p', '--profile',
                       dest='profilename',
                       help="name of the thunderbird-profile to use")
    oparser.add_option('-t', '--thunderbird-path',
                       dest='tbdirpath',
                       default="",
                       help="force path to thunderbird-userdir ")
    oparser.add_option('-c', '--create-target',
                       dest='createtarget',
                       action='store_true',
                       help=u"create rulelist if nonexistent. Default for cli: false, for gui: ask",
                       default=False)
    oparser.add_option('-n', '--no-gui',
                       dest='use_gui',
                       action='store_false',
                       default=True,
                       help=u"use cli (command line interface) (Default: False)",
                       )
    oparser.add_option('-s', '--skip-copy',
                       dest='mk_cpy',
                       action='store_false',
                       default=True,
                       help=u"no backup-copy in update-mode(Default: False)",
                       )
    oparser.add_option('-a', '--import-all',
                       dest='importall',
                       action='store_true',
                       default=False,
                       help=u"importiert all rules from source file (Default: False)",
                       )
    oparser.add_option('-m', '--emails',
                       dest='emails',
                       #action='store_true',
                       default=None,
                       help=u"(rule-)adresses to update, comma seperated list. Default: empty/gui:ask)",
                       )
    return oparser


def main():
    oparser = get_optparser()
    opts, args = oparser.parse_args()
    ui = buildUi(args, opts)
    ui.start()


if __name__ == '__main__':
    main()
