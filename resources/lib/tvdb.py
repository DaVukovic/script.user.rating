# -*- coding: utf-8 -*-

import xbmcgui
import xbmcaddon
import xbmc
import xbmcvfs
import os
import urllib
import httplib
import json
import re

__addon__               = xbmcaddon.Addon()
__addon_id__            = __addon__.getAddonInfo('id')
__addonname__           = __addon__.getAddonInfo('name')
__lang__                = __addon__.getLocalizedString
__datapath__            = xbmcvfs.translatePath(os.path.join('special://profile/addon_data/', __addon_id__)).replace('\\', '/') + '/'

import tools

API_KEY     = 'D460D7E8FF6842B6'
API_URL     = 'https://api.thetvdb.com/'
API_HOST    = 'api.thetvdb.com'

class TVDB:
    def __init__(self, master):
        self.login = __addon__.getSetting('loginTVDB') if master is True else __addon__.getSetting('loginTVDBsec')
        self.key  = __addon__.getSetting('keyTVDB') if master is True else __addon__.getSetting('keyTVDBsec')
        
    def sendRating(self, items):
        # check login
        if self.tryLogin() is False:
            debug.notify(self.login + ' - ' + __lang__(32110), True, 'TVDB')
            return
        
        item_count = len(items)
        item_added = 0
        bar = xbmcgui.DialogProgress()
        bar.create(__addonname__, '')
    
        for item in items:
            # bar
            item_added += 1
            p = int((float(100) / float(item_count)) * float(item_added))
            bar.update(p, str(item_added) + ' / ' + str(item_count) + ' - ' + item['title'])
            
            # search id
            if item['mType'] == 'tvshow':
                id = self.searchTVshowID(item)
                self.prepareRequest(id, 'user/ratings/series/', item['new_rating'])
            
            if item['mType'] == 'episode':
                episodeData = self.searchEpisodeID(item)
                tvshowid = self.searchTVshowID({'dbID': str(episodeData['tvshowid'])})
                ret = self.sendRequest('series/' + tvshowid + '/episodes/query', 'GET', get={'airedSeason': str(episodeData['season']), 'airedEpisode': str(episodeData['episode'])})
                if 'data' in ret and len(ret['data']) == 1 and 'id' in ret['data'][0]:
                    id = ret['data'][0]['id']
                else:
                    id = 0
                self.prepareRequest(id, 'user/ratings/episode/', item['new_rating'])
            
            if bar.iscanceled():
                bar.close()
                return
                
        bar.close()
        
        debug.debug('Rate sended to TVDB')
        debug.notify(self.login + ' - ' + __lang__(32101), False, 'TVDB')
        
    def prepareRequest(self, id, method, rating):
        if id == 0:
            debug.debug('No TVDB id found')
            debug.notify(__lang__(32102), True, 'TVDB')
            return
            
        # send rating
        if rating > 0:
            ret = self.sendRequest(method + str(id) + '/' + str(rating), 'PUT')
        else:
            ret = self.sendRequest(method + str(id), 'DELETE')
    
        if ret is not False:
            debug.debug('Rate sended to TVDB')
            debug.notify(self.login + ' - ' + __lang__(32101), False, 'TVDB')
        
    def getRated(self, type):
        # check login
        if self.tryLogin() is False:
            debug.notify(self.login + ' - ' + __lang__(32110), True, 'TVDB')
            return
        
        if 'tvshow' in type:
            method = 'series'
        if 'episode' in type:
            method = 'episode'
        
        rated = {}
        ret = self.sendRequest('user/ratings', 'GET')
        if 'data' in ret:
            for item in ret['data']:
                if item['ratingType'] == method:
                    
                    if 'tvshow' in type:
                        rated[str(item['ratingItemId'])] = item['rating']
                    
                    if 'episode' in type:
                        ret = self.sendRequest('episodes/' + str(item['ratingItemId']), 'GET')
                        if ret is not None and 'data' in ret:
                            if str(ret['data']['seriesId']) in rated.keys():
                                rated[str(ret['data']['seriesId'])].append({'season': ret['data']['airedSeason'], 'episode': ret['data']['airedEpisodeNumber'], 'rating': item['rating']})
                            else:
                                rated[str(ret['data']['seriesId'])] = [{'season': ret['data']['airedSeason'], 'episode': ret['data']['airedEpisodeNumber'], 'rating': item['rating']}]
        
        # transform TVDB ids to KODI DB ids
        kodiID = {}
        if 'tvshow' in type:
            jsonGet = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["title", "imdbnumber", "art"]}, "id": 1}')
            jsonGet = json.loads(unicode(jsonGet, 'utf-8', errors='ignore'))
            if 'result' in jsonGet and 'tvshows' in jsonGet['result']:
                for m in jsonGet['result']['tvshows']:
                    tvdb_search = re.search('tvdb', str(m))
                    if tvdb_search is not None and m['imdbnumber'] in rated.keys():
                        kodiID[m['tvshowid']] = {'title': m['title'], 'rating': rated[m['imdbnumber']]}
        
        if 'episode' in type:
            # KODI don't have site IDs for episodes
            # To get KODI IDs we must get TVshow ID and sseason and episode enum
            jsonGet = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["title", "imdbnumber", "art"]}, "id": 1}')
            jsonGet = json.loads(unicode(jsonGet, 'utf-8', errors='ignore'))
            if 'result' in jsonGet and 'tvshows' in jsonGet['result']:
                for m in jsonGet['result']['tvshows']:
                    tvdb_search = re.search('tvdb', str(m))
                    if tvdb_search is not None and m['imdbnumber'] in rated.keys():
                        tvshowid = str(m['tvshowid'])
                        
                        # for each tvshow that have rated episode get episodes list
                        jsonGetE = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": {"tvshowid": ' + tvshowid + ', "properties": ["title", "episode", "season"]}, "id": 1}')
                        jsonGetE = json.loads(unicode(jsonGetE, 'utf-8', errors='ignore'))
                        if 'result' in jsonGetE and 'episodes' in jsonGetE['result']:
                            for epi in jsonGetE['result']['episodes']:
                                
                                # for each episode check it exist in rated table
                                if m['imdbnumber'] in rated.keys():
                                    for r in rated[m['imdbnumber']]:
                                        if epi['season'] == r['season'] and epi['episode'] == r['episode']:
                                            kodiID[epi['episodeid']] = {'title': m['title'] + ' - ' + epi['title'], 'rating': r['rating']}
        return kodiID
        
    def searchTVshowID(self, item):
        jsonGet = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShowDetails", "params": {"tvshowid": ' + str(item['dbID']) + ', "properties": ["imdbnumber", "art"]}, "id": 1}')
        jsonGet = unicode(jsonGet, 'utf-8', errors='ignore')
        jsonGetResponse = json.loads(jsonGet)
        debug.debug('searchTVshowID: ' + str(jsonGetResponse))
        tvdb_search = re.search('thetvdb', str(jsonGetResponse))
        if tvdb_search is not None and 'result' in jsonGetResponse and 'tvshowdetails' in jsonGetResponse['result'] and 'imdbnumber' in jsonGetResponse['result']['tvshowdetails']:
            id = jsonGetResponse['result']['tvshowdetails']['imdbnumber']
        else:
            id = 0
        return id
    
    def searchEpisodeID(self, item):
        jsonGet = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodeDetails", "params": {"episodeid": ' + str(item['dbID']) + ', "properties": ["season", "episode", "tvshowid"]}, "id": 1}')
        jsonGet = unicode(jsonGet, 'utf-8', errors='ignore')
        jsonGetResponse = json.loads(jsonGet)
        debug.debug('searchEpisodeID: ' + str(jsonGetResponse))
        if 'result' in jsonGetResponse and 'episodedetails' in jsonGetResponse['result'] and 'tvshowid' in jsonGetResponse['result']['episodedetails']:
            epiosdeData = jsonGetResponse['result']['episodedetails']
        else:
            episodeData = {}
        return epiosdeData
    
    def tryLogin(self):
        self.token = ''
        ret = self.sendRequest('login', 'POST', post={"apikey": API_KEY, "username": self.login, "userkey": self.key})
        if ret is not False and 'token' in ret:
            self.token = str(ret['token'])
            return True
        return False
    
    def sendRequest(self, method, http_method, get={}, post={}):
        
        if len(get) > 0:
            get = '?' + urllib.urlencode(get)
        else:
            get = ''
        post = json.dumps(post)
        
        # send request
        headers = {
            'Content-type': 'application/json', 
            'Accept': 'application/json',
            'Authorization': 'Bearer ' + self.token
            }
        
        # send request
        req = httplib.HTTPSConnection(API_HOST)
        req.request(http_method, API_URL + method + get, post, headers)
        response = req.getresponse()
        html = response.read()
        debug.debug('Request: ' + html)
        if response.status != 200 and response.status != 201:
            debug.debug('[ERROR ' + str(response.status) + ']: ' + html)
            return False
        
        # get json
        try:
            output = unicode(html, 'utf-8', errors='ignore')
            output = json.loads(output)
        except Exception as Error:
            debug.debug('[GET JSON ERROR]: ' + str(Error))
            return {}
            
        return output
    