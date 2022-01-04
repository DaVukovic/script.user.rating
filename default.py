# -*- coding: utf-8 -*-

import xbmcgui
import xbmc
import sys
import xbmcaddon
from resources.lib.tools import debug, jsonrpc
from resources.lib.syncData import SYNC
import resources.lib.rateDialog as rateDialog

__addon__ = xbmcaddon.Addon()
__addon_id__ = __addon__.getAddonInfo('id')
__icon__ = __addon__.getAddonInfo('icon')


class GUI(object):
    def __init__(self):

        debug('Starting GUI...')
        self.main()

    def main(self):

        # declarate media type
        d_for = ['movie', 'tvshow', 'episode']
        item = {}

        # open sync dialog if no parameter
        if len(sys.argv) == 0 or len(sys.argv[0]) == 0:
            debug('Starting Rating Dialog...')
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
            item['rating'] = 0 if xbmc.getInfoLabel('ListItem.UserRating') == "" else \
                int(xbmc.getInfoLabel('ListItem.UserRating'))
            item['title'] = xbmc.getInfoLabel('ListItem.Title')

        debug('RunFromService', self.runFromService)
        debug('Retrieved data',
              'RATING: %s, MEDIA: %s, ID: %s, TITLE: %s' % (item['rating'], item['mType'], item['dbID'], item['title']))

        if item['mType'] not in d_for:
            debug('Unsupported media type, exiting', item['mType'])
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
        if 'true' in __addon__.getSetting('enableTMDBsec') \
                or 'true' in __addon__.getSetting('enableFILMWEBsec') \
                or 'true' in __addon__.getSetting('enableTVDBsec'):

            item['new_rating'] = rateDialog.DIALOG().start(item, __addon__.getSetting('profilNamesec'))
            if item['new_rating'] is not None:
                self.sendToWebsites(item, False)

    def getData(self, dbID, mType):
        query = {'method': 'VideoLibrary.Get%sDetails' % mType.capitalize(),
                 'params': {'properties': ['title', 'userrating'], '%sid' % mType: int(dbID)}}
        res = jsonrpc(query)

        title = ''
        rating = 0
        if res:
            title = res['%sdetails' % mType]['title']
            rating = res['%sdetails' % mType]['userrating']

        return {'dbID': dbID, 'mType': mType, 'title': title, 'rating': rating}

    def addVote(self, item):
        query = {'method': 'VideoLibrary.Set%sDetails' % item['mType'].capitalize(),
                 'params': {'%sid' % item['mType']: int(item['dbID']), 'userrating': int(item['new_rating'])}}
        debug('Query', query)
        res = jsonrpc(query)
        if res:
            debug('Voting updated', item['mType'].title())

    def sendToWebsites(self, item, master):

        pass
        '''
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
        '''


# lock script to prevent duplicates
if xbmcgui.Window(10000).getProperty(__addon_id__ + '_running') != 'True':
    GUI()
    xbmcgui.Window(10000).clearProperty(__addon_id__ + '_running')
