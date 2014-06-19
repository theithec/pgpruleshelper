#! /usr/bin/env python
# -*- coding: utf-8 -*-
'''
1.Sucht Adressen aus einer pgprules (1. Argument) in Akanodi-Kontakten
2.Wenn vorhanden UND bereits Verschlüsselungskeys eingetragen sind,
werden die Kontakte aktualisiert.
pgprulehelpers sonstige Argumente und Optionen werden ignoriert'''

from PyQt4 import QtGui
from PyKDE4.akonadi import Akonadi as A
from PyKDE4.kdeui import  KMessageBox
import os
import vobject

from pgpruleshelper import mailval, get_optparser, buildUi, Cli


CONTACT_MIME_TYPES = [
    "text/directory",
    "application/x-vnd.akonadi.collection.virtual"
]


def  get_contact_root_collections():
    job = A.CollectionFetchJob(
        A.Collection.root(),
        A.CollectionFetchJob.Recursive
    )
    job.fetchScope().setContentMimeTypes(CONTACT_MIME_TYPES)
    if job.exec_():
        return job.collections()


def get_contactitem_and_vobject__by_email(coll, email):
    job = A.ItemFetchJob(coll)
    job.fetchScope().fetchFullPayload()
    if job.exec_():
        for item in job.items():
            pl = item.payloadData()
            if not pl:
                continue
            vobj = vobject.readOne("%s" % pl)
            fn = getattr(vobj, "email", None)
            if fn and fn.value.lower().startswith(email.lower()):
                return (item, vobj)


def update_item(item, vobj, ids):
    vobj.contents['x-kaddressbook-openpgpfp'][0].value = ids
    item.setPayloadFromData(vobj.serialize())
    job = A.ItemModifyJob(item)
    return job.exec_()


class Kli(Cli, QtGui.QApplication):
    def __init__(self, args, opts):
        QtGui.QApplication.__init__(self, [])
        Cli.__init__(self, args, opts)
        self.crcs = get_contact_root_collections()

    def msg(self, msg):
        KMessageBox.information(self.parent(), msg, "Kpgpruleshelper")

    def start(self):
        imported = []
        not_imported = []
        msg_ = ''
        self.source = self.getSource()
        selected_rules = self.getSelectedRules()
        found = False
        for sr in selected_rules:
            contact = mailval(sr)
            for crc in self.crcs:
                found = get_contactitem_and_vobject__by_email(crc, contact)
                if found:
                    break
            if found:
                item, vobj = found
                ids = sr.attributes['keyId'].value
                try:
                    update_item(item, vobj, ids)
                except KeyError, e:
                    msg_ += (u"%sKeyError:%s%s(%s)" % (
                        os.linesep, os.linesep, e, contact))
                    not_imported.append(contact)
                    continue
                imported.append(contact)
                found = False
            else:
                not_imported.append(contact)
        if imported:
            msg_ += u"%sImportiert:%s%s" % (
                os.linesep, os.linesep, os.linesep.join(imported))
        else:
            msg_ += u'Nichts importiert!'
        if not_imported:
            msg_ += u"%sNicht importiert:%s%s" % (
                os.linesep, os.linesep, os.linesep.join(not_imported))
        self.msg(msg_)


def main():
    oparser = get_optparser()
    opts, args = oparser.parse_args()
    opts.importall = True
    opts.use_gui = True
    ui = buildUi(args, opts, UiCls=Kli)
    ui.start()


if __name__ == '__main__':
    main()

