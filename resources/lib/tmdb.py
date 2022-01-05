# -*- coding: utf-8 -*-
import socket
import xbmcaddon
import xbmc
import xbmcgui
import xbmcvfs
import os
import requests
import http.client as httplib
from urllib.parse import urlencode
import json
import re

__addon__ = xbmcaddon.Addon()
__addon_id__ = __addon__.getAddonInfo('id')
__addonname__ = __addon__.getAddonInfo('name')
__lang__ = __addon__.getLocalizedString
__datapath__ = os.path.join(xbmcvfs.translatePath(__addon__.getAddonInfo('profile')), 'tmdb')

from . import tools

API_KEY = '1009b5cde25c7b0692d51a7db6e49cbd'
API_URL = 'https://api.themoviedb.org/3/'
API_HOST = 'api.themoviedb.org/'


class TMDB:
    def __init__(self, master):
        self.login = __addon__.getSetting('loginTMDB') if master is True else __addon__.getSetting('loginTMDBsec')
        self.passwd = __addon__.getSetting('passTMDB') if master is True else __addon__.getSetting('passTMDBsec')
        self.session_id = None

    def sendRating(self, item):
        # check login
        if not self.tryLogin():
            tools.notify( __lang__(32110) % self.login, force=True, icon=xbmcgui.NOTIFICATION_ERROR)
            return

        ret = False
        if item['mType'] == 'movie':
            imdb = self.searchMovieID(item)
            ret = self.prepareRequest('movie/', str(imdb), '/rating', item['new_rating'])

        elif item['mType'] == 'tvshow':
            imdb = self.searchTVshowID(item)
            ret = self.prepareRequest('tv/', str(imdb), '/rating', item['new_rating'])

        elif item['mType'] == 'episode':
            episodeData = self.searchEpisodeID(item)
            tvshowid = self.searchTVshowID({'dbID': episodeData['tvshowid']})
            ret = self.prepareRequest('tv/',  str(tvshowid), '/season/' + str(episodeData['season']) +
                                      '/episode/' + str(episodeData['episode']) + '/rating', item['new_rating'])
        if not ret: return False

        tools.debug('TMDB rating', 'send %s for %s \'%s\'' % (item['new_rating'], item['mType'], item['title']))
        tools.notify(__lang__(32101) % self.login, force=False)
        
    def prepareRequest(self, endpoint, imdb, opt, rating):
        try:
            r = requests.post(API_URL + endpoint + imdb + opt,
                              params={'api_key': API_KEY, 'session_id': self.session_id},
                              data={'value': rating})
            r.raise_for_status()
            return r.json().get('success', False)

        except (socket.gaierror, requests.HTTPError, requests.ConnectionError) as e: tools.debug(e)
        return False

    def getRated(self, type):
        # check login
        if self.tryLogin() is False:
            tools.notify( __lang__(32110) % self.login, force=True, icon=xbmcgui.NOTIFICATION_ERROR)
            return False
        
        if 'movie' in type:
            method = 'movies'
        if 'tvshow' in type:
            method = 'tv'
        if 'episode' in type:
            method = 'tv/episodes'
        
        # read all pages from API
        page = 1
        rated = {}
        while True:
            ret = self.sendRequest('account/' + self.account + '/rated/' + method, 'GET', {'session_id': self.session_id, 'page': page})
            if ret is False or 'total_pages' not in ret or 'page' not in ret or 'results' not in ret:
                return False
                
            for item in ret['results']:
                rating = int(round(float(item['rating'])))
                if rating > 0:
                    if 'movie' in type:
                        # get external source
                        ext = self.sendRequest('movie/' + str(item['id']), 'GET', {'session_id': self.session_id})
                        if 'imdb_id' in ext:
                            rated[str(ext['imdb_id'])] = rating
                    if 'tvshow' in type:
                        rated[str(item['id'])] = rating
                    if 'episode' in type:
                        if str(item['show_id']) in rated.keys():
                            rated[str(item['show_id'])].append({'season': item['season_number'], 'episode': item['episode_number'], 'rating': rating})
                        else:
                            rated[str(item['show_id'])] = [{'season': item['season_number'], 'episode': item['episode_number'], 'rating': rating}]
                        
            if page >= ret['total_pages']:
                break
            page = ret['page'] + 1
            
        # transform tmdb ids to KODI DB ids
        kodiID = {}
        if 'movie' in type:
            jsonGet = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"properties": ["title", "imdbnumber", "art"]}, "id": 1}')
            jsonGet = json.loads(jsonGet)
            if 'result' in jsonGet and 'movies' in jsonGet['result']:
                for m in jsonGet['result']['movies']:
                    tmdb_search = re.search('tmdb', str(m))
                    if tmdb_search is not None and m['imdbnumber'] in rated.keys():
                        kodiID[m['movieid']] = {'title': m['title'], 'rating': rated[m['imdbnumber']]}
        
        if 'tvshow' in type:
            jsonGet = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["title", "imdbnumber", "art"]}, "id": 1}')
            jsonGet = json.loads(jsonGet)
            if 'result' in jsonGet and 'tvshows' in jsonGet['result']:
                for m in jsonGet['result']['tvshows']:
                    tmdb_search = re.search('tmdb', str(m))
                    if tmdb_search is not None and m['imdbnumber'] in rated.keys():
                        kodiID[m['tvshowid']] = {'title': m['title'], 'rating': rated[m['imdbnumber']]}
                        
        if 'episode' in type:
            # KODI don't have site IDs for episodes
            # To get KODI IDs we must get TVshow ID and sseason and episode enum
            jsonGet = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["title", "imdbnumber", "art"]}, "id": 1}')
            jsonGet = json.loads(jsonGet)
            if 'result' in jsonGet and 'tvshows' in jsonGet['result']:
                for m in jsonGet['result']['tvshows']:
                    tmdb_search = re.search('tmdb', str(m))
                    if tmdb_search is not None and m['imdbnumber'] in rated.keys():
                        tvshowid = str(m['tvshowid'])
                        
                        # for each tvshow that have rated episode get episodes list
                        jsonGetE = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": {"tvshowid": ' + tvshowid + ', "properties": ["title", "episode", "season"]}, "id": 1}')
                        jsonGetE = json.loads(jsonGetE)
                        if 'result' in jsonGetE and 'episodes' in jsonGetE['result']:
                            for epi in jsonGetE['result']['episodes']:
                                
                                # for each episode check it exist in rated table
                                if m['imdbnumber'] in rated.keys():
                                    for r in rated[m['imdbnumber']]:
                                        if epi['season'] == r['season'] and epi['episode'] == r['episode']:
                                            kodiID[epi['episodeid']] = {'title': m['title'] + ' - ' + epi['title'], 'rating': r['rating']}
        return kodiID
    
    def searchMovieID(self, item):
        query = {'method': 'VideoLibrary.GetMovieDetails',
                 'params': {'movieid': item['dbID'], 'properties': ['imdbnumber']}}
        res = tools.jsonrpc(query)
        if res: return res['moviedetails'].get('imdbnumber', 0)
        return False

    def searchTVshowID(self, item):
        query = {'method': 'VideoLibrary.GetTVShowDetails',
                 'params': {'tvshowid': item['dbID'], 'properties': ['imdbnumber']}}
        res = tools.jsonrpc(query)
        if res: return res['tvshowdetails'].get('imdbnumber', 0)
        return False

    def searchEpisodeID(self, item):
        query = {'method': 'VideoLibrary.GetEpisodeDetails',
                 'params': {'episodeid': item['dbID'], 'properties': ['season', 'episode', 'tvshowid']}}
        res = tools.jsonrpc(query)
        if res: return res.get('episodedetails')
        return False

    def tryLogin(self):
        if self.session_id is None:
            user, self.session_id = self.get_sid(__datapath__, username=self.login)
            tools.debug('TMDB', 'SID for %s from file: %s' % (user, self.session_id))
        try:
            if self.session_id:
                r = requests.get(API_URL + 'account', params={'api_key': API_KEY, 'session_id': self.session_id})
                if r.json().get('id', False):
                    tools.debug('TMDB', 'Valid session')
                    return True
                else:
                    self.session_id = None

            if not self.session_id:

                if not self.login:
                    # create guest session
                    tools.debug('TMDB','create guest session')
                    r = requests.get(API_URL + 'authentication/guest_session/new', params={'api_key': API_KEY})
                    r.raise_for_status()
                    if r.json().get('success', False):
                        self.set_sid(__datapath__, r.json().get('guest_session_id', False), 'guest')
                        return True
                else:
                    # create user session with authentication
                    print('create user session with authentication')
                    r = requests.get(API_URL + 'authentication/token/new', params={'api_key': API_KEY})
                    r.raise_for_status()
                    token = r.json().get('request_token', False)
                    if token:
                        r = requests.get(API_URL + 'authentication/token/validate_with_login',
                                         params={'api_key': API_KEY,
                                                 'request_token': token, 'username': self.login,
                                                 'password': self.passwd})
                        r.raise_for_status()
                        if r.json().get('success', False):
                            r = requests.get(API_URL + 'authentication/session/new',
                                             params={'api_key': API_KEY, 'request_token': token})
                            self.set_sid(__datapath__, r.json().get('session_id', False), self.login)
                            return True

        except (socket.gaierror, requests.HTTPError, requests.ConnectionError) as e: tools.debug(e)
        return False

    def get_sid(self, file, username=None):
        if username is None: username = 'guest'
        account_data = dict()
        if os.path.exists(file):
            with open(file, 'r') as f: account_data = json.loads(f.read())
        if username in account_data.keys(): return username, account_data.get(username, False)
        return username, None

    def set_sid(self, file, session_id, username=None):
        if username is None: username = 'guest'
        account_data = dict()
        if os.path.exists(file):
            with open(file, 'r') as f: account_data = json.loads(f.read())
        print(username, session_id)
        account_data.update({username: session_id})
        with open(file, 'w') as f:
            f.write(json.dumps(account_data))
        return True

    def sendRequest(self, method, http_method, get={}, post={}):
        # prepare values
        get['api_key'] = API_KEY
        
        get = urlencode(get)
        post = urlencode(post)
        
        # send request
        req = httplib.HTTPSConnection(API_HOST)
        req.request(http_method, API_URL + method + '?' + get, post)
        response = req.getresponse()
        html = response.read()
        tools.debug('Request', html)
        if response.status != 200 and response.status != 201:
            tools.debug('ERROR ' + str(response.status), html)
            return False
        
        # get json
        try:
            output = html
            output = json.loads(output)
        except Exception as Error:
            tools.debug('[GET JSON ERROR]: ' + str(Error))
            return {}
            
        return output

    