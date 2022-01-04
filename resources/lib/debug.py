# -*- coding: utf-8 -*-

import xbmc
import xbmcaddon
import xbmcgui

__addon__               = xbmcaddon.Addon()
__icon__                = __addon__.getAddonInfo('icon')
__addonname__           = __addon__.getAddonInfo('name')


def debug(msg):
    if 'true' in __addon__.getSetting('debug'):
        xbmc.log('[' + __addonname__ + '] ' + str(msg))


def notify(msg, force=False, title=''):
    if 'true' in __addon__.getSetting('notify') or force is True:
        xbmcgui.Dialog().notification(__addonname__, title, __icon__, 4000)
