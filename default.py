# -*- coding: utf-8 -*-

import json
import xbmcgui
import xbmc
import sys
import os
import xbmcaddon
import xbmcvfs
from resources.lib.debug import debug
from resources.lib.syncData import SYNC
import resources.lib.rateDialog as rateDialog

__addon__               = xbmcaddon.Addon()
__addon_id__            = __addon__.getAddonInfo('id')
__addonname__           = __addon__.getAddonInfo('name')
__icon__                = __addon__.getAddonInfo('icon')
__addonpath__           = xbmcvfs.translatePath(__addon__.getAddonInfo('path'))
__lang__                = __addon__.getLocalizedString
__path__                = os.path.join(__addonpath__, 'resources', 'lib')
__path_img__            = os.path.join(__addonpath__, 'resources', 'media')


class GUI(object):
    def __init__(self):
        
        self.main()
        
    def main(self):
        
        # declarate media type
        d_for = ['movie', 'tvshow', 'episode']
        
        item = {}
        
        # open sync dialog if no parameter
        if len(sys.argv) == 0 or len(sys.argv[0]) == 0:
            SYNC().start()
            return
        
        # detect that user or service run script
        if len(sys.argv) > 3:
            self.runFromService = True
            item = self.getData(sys.argv[2], sys.argv[3])

        else:
            self.runFromService = False
            item['mType'] = xbmc.getInfoLabel('ListItem.DBTYPE')
            item['dbID'] = xbmc.getInfoLabel('ListItem.DBID')
            item['rating'] = 0 if xbmc.getInfoLabel('ListItem.UserRating') == "" else int(xbmc.getInfoLabel('ListItem.UserRating'))
            item['title'] = xbmc.getInfoLabel('ListItem.Title')
        
        debug('Retrieve data from Database: RATING: %s, MEDIA: %s, ID: %s, TITLE: %s' % (item['rating'],
                                                                                         item['mType'],
                                                                                         item['dbID'],
                                                                                         item['title']))
        
        if item['mType'] not in d_for:
            debug('No data, exiting...')
            return
        
        # check conditions from settings
        if self.runFromService:
            if 'true' in __addon__.getSetting('onlyNotRated') and item['rating'] > 0:
                debug('Could only rate non-rated media due settings, exiting...')
                return
        
        # display window rating

        item['new_rating'] = rateDialog.DIALOG().start(item, __addon__.getSetting('profileName'))
        if item['new_rating'] is not None:
            self.addVote(item)
            self.sendToWebsites(item, True)
            
        # display window rating for second profile
        if 'true' in __addon__.getSetting('enableTMDBsec') or 'true' in __addon__.getSetting('enableFILMWEBsec') or 'true' in __addon__.getSetting('enableTVDBsec'):
            item['new_rating'] = rateDialog.DIALOG().start(item, __addon__.getSetting('profilNamesec'))
            if item['new_rating'] is not None:
                self.sendToWebsites(item, False)
            
    def getData(self, dbID, mType):
        jsonGetSource = '{"jsonrpc": "2.0", "method": "VideoLibrary.Get' + mType.title() + 'Details", "params": { "properties" : ["title", "userrating"], "' + mType + 'id": ' + str(dbID) + '}, "id": "1"}'
        jsonGetSource = xbmc.executeJSONRPC(jsonGetSource)
        jsonGeResponse = json.loads(jsonGetSource)
        
        debug(str(jsonGeResponse))
        
        if 'result' in jsonGeResponse and mType + 'details' in jsonGeResponse['result']:
            title = jsonGeResponse['result'][mType + 'details']['title'].encode('utf-8')
            rating = jsonGeResponse['result'][mType + 'details']['userrating']
        else:
            title = ""
            rating = 0
            
        return { 'dbID': dbID, 'mType': mType, 'title': title, 'rating': rating }
        
    def addVote(self, item):
        jsonAdd = '{"jsonrpc": "2.0", "id": 1, "method": "VideoLibrary.Set' + item['mType'].title() + 'Details", "params": {"' + item['mType'] + 'id" : ' + item['dbID'] + ', "userrating": ' + str(item['new_rating']) + '}}'
        xbmc.executeJSONRPC(jsonAdd)

    def sendToWebsites(self, item, master):
        # send rate to tmdb
        if 'true' in __addon__.getSetting('enableTMDB' + item['mType']):
            import resources.lib.tmdb as tmdb
            tmdb.TMDB(master).sendRating([item])
            
        # send rate to tvdb
        if 'true' in __addon__.getSetting('enableTVDB' + item['mType']):
            import resources.lib.tvdb as tvdb
            tvdb.TVDB(master).sendRating([item])
            
        # send rate to filmweb
        if 'true' in __addon__.getSetting('enableFILMWEB' + item['mType']):
            import resources.lib.filmweb as filmweb
            filmweb.FILMWEB(master).sendRating([item])


# lock script to prevent duplicates
if xbmcgui.Window(10000).getProperty(__addon_id__ + '_running') != 'True':
    debug('Starting GUI...')
    GUI()
    xbmcgui.Window(10000).clearProperty(__addon_id__ + '_running')
