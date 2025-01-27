# -*- coding: utf-8 -*-

import xbmcaddon
import xbmcgui
import xbmc
import xbmcvfs
import os

__addon__               = xbmcaddon.Addon()
__addon_id__            = __addon__.getAddonInfo('id')
__addonpath__           = xbmcvfs.translatePath(__addon__.getAddonInfo('path'))

class DIALOG:
    def start(self, xml_file, labels={}, textboxes={}, buttons=[], list=0):
        
        display = SHOW(xml_file, __addonpath__, labels=labels,  textboxes=textboxes, buttons=buttons, list=list)
        
        display.doModal()
        ret = display.ret
        del display
        return ret
        
class SHOW(xbmcgui.WindowXMLDialog):
    
    def __init__(self, xmlFile, resourcePath, labels, textboxes, buttons, list):
        
        self.ret = None
        self.labels = labels
        self.textboxes = textboxes
        self.buttons = buttons
        self.list = list
        
    def onInit(self):
        
        # set labels
        for label, label_text in self.labels.items():
            self.getControl(label).setLabel(label_text)
        
        # set textboxes
        for textbox, textbox_text in self.textboxes.items():
            self.getControl(textbox).setText(textbox_text)
            
        # set buttons
        self.listitem = self.getControl(self.list)
        for button_text in self.buttons:
            self.listitem.addItem(xbmcgui.ListItem(button_text))
        
        # focus on list
        self.setFocus(self.listitem)
        
        # set amount of buttons for background height
        xbmcgui.Window(10000).setProperty(__addon_id__ + '_items',str(len(self.buttons)))
        
    def onClick(self, controlID):
        # return selected button
        self.ret = self.getControl(controlID).getSelectedPosition()
        self.close()
