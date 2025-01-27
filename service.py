# -*- coding: utf-8 -*-

import xbmc
import xbmcvfs
import xbmcaddon
import json
from resources.lib.tools import debug

__addon__ = xbmcaddon.Addon()
__addon_id__ = __addon__.getAddonInfo('id')
__addonname__ = __addon__.getAddonInfo('name')
__icon__ = __addon__.getAddonInfo('icon')
__addonpath__ = xbmcvfs.translatePath(__addon__.getAddonInfo('path'))


class Monitor(xbmc.Monitor):

    def __init__(self):
        xbmc.Monitor.__init__(self)
        self.item = None

    def onNotification(self, sender, method, data):

        media = []

        if 'true' in __addon__.getSetting('onWatchedMovie'):
            media.append('movie')
        if 'true' in __addon__.getSetting('onWatchedEpisode'):
            media.append('episode')

        if method == 'Player.OnStop' or method == 'Player.OnPlay':
            data = json.loads(data)
            if 'item' in data and 'id' in data['item'] and 'type' in data['item']:
                self.item = data['item']
                debug(method, str(self.item))

        if method == 'VideoLibrary.OnUpdate':
            data = json.loads(data)
            if 'playcount' in data and data['playcount'] > 0:
                if 'item' in data and 'type' in data['item'] and data['item']['type'] in media and 'id' in data['item']:
                    idDB = data['item']['id']
                    mType = data['item']['type']
                    debug(method, str(data))
                    if self.item is not None and self.item['id'] == idDB and self.item['type'] == mType:
                        debug('Service', 'Try to run script...')
                        xbmc.executebuiltin(
                            'RunScript(' + __addon_id__ + ', ' + method + ', ' + str(idDB) + ', ' + mType + ')')


monitor = Monitor()

while not monitor.abortRequested():
    xbmc.sleep(10000)
