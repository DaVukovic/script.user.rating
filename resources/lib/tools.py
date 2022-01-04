# -*- coding: utf-8 -*-

import xbmc
import xbmcaddon
import xbmcgui
import json

__addon__ = xbmcaddon.Addon()
__icon__ = __addon__.getAddonInfo('icon')
__addon_id__ = __addon__.getAddonInfo('id')
__addonname__ = __addon__.getAddonInfo('name')


def debug(msg, content=''):
    if 'true' in __addon__.getSetting('debug'):
        if content:
            if type(content) is bytes: content = content.decode()
            xbmc.log('[%s] %s: %s' % (__addon_id__, msg, str(content)))
        else:
            xbmc.log('[%s] %s' % (__addon_id__, msg))


def notify(msg, force=False, title=''):
    if 'true' in __addon__.getSetting('notify') or force is True:
        xbmcgui.Dialog().notification(__addonname__, title, __icon__, 4000)


def jsonrpc(query, id=1):
    querystring = {"jsonrpc": "2.0", "id": id}
    querystring.update(query)
    try:
        response = json.loads(xbmc.executeJSONRPC(json.dumps(querystring)))
        if 'result' in response:
            return response['result']
    except TypeError as e:
        xbmc.log('Error executing JSON RPC: %s' % e, xbmc.LOGERROR)
    return False
