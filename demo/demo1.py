#!/usr/bin/env python
import os
import re
import logging
import platform
import pickle
import xml.etree.ElementTree as ET

import tkinter as tk
from tkinter.filedialog import askopenfilename
from tkinter import scrolledtext

import gifts


class TextHandler(logging.Handler):

    def __init__(self, widget):

        logging.Handler.__init__(self)
        self.textWidget = widget
    #
    # Override base 'emit' method. Instead write the message to the text widget

    def emit(self, record):

        msg = self.format(record)

        def append():

            self.textWidget.configure(state=tk.NORMAL)
            self.textWidget.insert(tk.END, msg + '\n')
            self.textWidget.configure(state=tk.DISABLED)
            self.textWidget.yview(tk.END)

        self.textWidget.after(0, append)


class simpleGUI(object):

    def __init__(self):
        #
        # Build the GUI first
        self.window = tk.Tk()
        self.window.title('Generate IWXXM From TAC Demonstrator')

        self.window.rowconfigure(0, weight=1, minsize=50)
        self.window.rowconfigure(1, weight=1, minsize=80)
        self.window.rowconfigure(2, weight=1, minsize=50)

        frame_a = tk.Frame(master=self.window, relief=tk.GROOVE, borderwidth=2)
        frame_a.pack(fill=tk.X)

        self.btn_tac = tk.Button(master=frame_a, text='TAC File:')
        self.btn_tac.bind('<Button-1>', self.open_file)
        self.btn_tac.grid(row=0, column=0, sticky='e')

        self.ent_tac = tk.Entry(master=frame_a, width=80)
        self.ent_tac.grid(row=0, column=1, sticky='ew')

        lbl_box = tk.Label(master=frame_a, text='Activity Msgs:')
        lbl_box.grid(row=1, column=0, sticky='ne')

        self.scrld_txt = scrolledtext.ScrolledText(master=frame_a, width=80)
        self.scrld_txt.grid(row=1, column=1, sticky='ew')

        lbl_xml = tk.Label(master=frame_a, text='IWXXM XML File:')
        lbl_xml.grid(row=2, column=0, sticky='e')

        self.ent_xml = tk.Entry(master=frame_a, width=80)
        self.ent_xml.grid(row=2, column=1, sticky='ew')

        frame_b = tk.Frame(master=self.window, relief=tk.GROOVE, borderwidth=5)
        frame_b.pack(fill=tk.X)

        self.btn_gift = tk.Button(master=frame_b, text='Generate IWXXM From TAC')
        self.btn_gift.bind('<Button-1>', self.encode)
        self.btn_gift.pack(side=tk.LEFT)

        btn_clear = tk.Button(master=frame_b, text='Clear')
        btn_clear.bind('<Button-1>', self.clear_fields)
        btn_clear.pack(side=tk.LEFT)
        #
        # Set up logging
        logging.basicConfig(filename='demo.log', level=logging.INFO, format='%(levelname)s: %(message)s')
        self.logger = logging.getLogger()
        #
        # Direct python logging output to the scrolled text widget
        encoderActivity = TextHandler(self.scrld_txt)
        self.logger.addHandler(encoderActivity)
        #
        # Now get GIFT software set up
        if platform.system() == 'Windows':
            with open('aerodromes.win.db', 'rb') as _fh:
                aerodromes = pickle.load(_fh)
        else:
            with open('aerodromes.db', 'rb') as _fh:
                aerodromes = pickle.load(_fh)
        #
        # Regular expressions to identify TAC file contents based on WMO AHL line
        self.encoders = []
        self.encoders.append((re.compile(r'^S(A|P)[A-Z][A-Z]\d\d\s+[A-Z]{4}\s+\d{6}', re.MULTILINE),
                              gifts.METAR.Encoder(aerodromes)))
        self.encoders.append((re.compile(r'^FN[A-Z][A-Z]\d\d\s+[A-Z]{4}\s+\d{6}', re.MULTILINE),
                              gifts.SWA.Encoder()))
        self.encoders.append((re.compile(r'^FT[A-Z][A-Z]\d\d\s+[A-Z]{4}\s+\d{6}', re.MULTILINE),
                              gifts.TAF.Encoder(aerodromes)))
        self.encoders.append((re.compile(r'FK\w\w\d\d\s+[A-Z]{4}\s+\d{6}', re.MULTILINE), gifts.TCA.Encoder()))
        self.encoders.append((re.compile(r'FV\w\w\d\d\s+[A-Z]{4}\s+\d{6}', re.MULTILINE), gifts.VAA.Encoder()))

    def encode(self, *event):

        tacFile = self.ent_tac.get()
        with open(tacFile, 'r') as input_file:
            tacText = input_file.read()

        encoder = result = None
        for regexp, encoder in self.encoders:
            result = regexp.search(tacText)
            if result is not None:
                break
        else:
            self.logger.error('No match on WMO AHL patterns')
            encoder = None

        if encoder is not None:

            bulletin = encoder.encode(tacText[result.start():])
            for xml in bulletin:

                tree = ET.XML(ET.tostring(xml))
                icaoID = tree.find('.//*{http://www.aixm.aero/schema/5.1.1}locationIndicatorICAO')
                if icaoID is not None:
                    msg = '%s: SUCCESS' % icaoID.text
                    self.logger.info(msg)
                else:
                    self.logger.info('IWXXM Advisory created!')
            #
            # Write the Meteorological Bulletin containing IWXXM documents in the same directory
            bulletin.write()

            self.ent_xml.delete(0, tk.END)
            self.ent_xml.insert(0, bulletin.get_bulletinIdentifier())
            self.ent_xml['state'] = tk.NORMAL

        self.btn_gift['state'] = tk.NORMAL

    def open_file(self, *event):

        filepath = askopenfilename(initialdir=os.getcwd(), filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if not filepath:
            return

        self.ent_tac.delete(0, tk.END)
        self.ent_tac.insert(0, filepath)
        self.btn_tac['state'] = tk.NORMAL

    def clear_fields(self, *args):

        self.ent_tac.delete(0, tk.END)
        self.ent_xml.delete(0, tk.END)
        self.scrld_txt['state'] = tk.NORMAL
        self.scrld_txt.delete("1.0", tk.END)
        self.scrld_txt['state'] = tk.DISABLED


if __name__ == '__main__':

    gui = simpleGUI()
    gui.window.mainloop()
