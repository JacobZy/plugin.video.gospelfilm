# -*- coding: utf-8 -*-
import re
import json
import gzip
import base64
import time
import urllib
import urllib2
import httplib
from StringIO import StringIO
from xbmcswift2 import xbmc
from xbmcswift2 import Plugin
from xbmcswift2 import xbmcgui
try:
    from ChineseKeyboard import Keyboard
except:
    from xbmc import Keyboard

plugin = Plugin()
dialog = xbmcgui.Dialog()
epcache = plugin.get_storage('epcache', TTL=1440)

baseurl = r'http://www.fyyy7.com'

@plugin.route('/')
def showcatalog():
    """
    show catalog list
    """
    if baseurl in epcache:
        return epcache[baseurl]
    result = _http(baseurl)
    catastr = re.search(r'<div class="menu".*?<ul>(.*?)</ul>',
                        result, re.S)
    catalogs = re.findall(r'<li class="letter_3"><a href="(.*?)">(.*?)</a>', catastr.group(1),re.S)
    menus = [{
        'label': catalog[-1],
        'path': plugin.url_for('showlist',
                               url='{0}'.format(
                                   catalog[0])),
    } for catalog in catalogs]
    menus.insert(0, {'label': '【[COLOR FFFF0000]搜索视频[/COLOR]】选择', 'path': plugin.url_for('searchvideo')})
    menus.append({'label': '热门视频', 'path': plugin.url_for('hotlist')})
    menus.append({'label': '手动清除缓存【缓存24小时自动失效】',
                  'path': plugin.url_for('clscache')})
    epcache[baseurl] = menus
    return menus

@plugin.route('/hotlist')
def hotlist():
    """
    show hot movie list
    """
    if 'hot' in epcache:
        return epcache['hot']

    result = _http(baseurl)

    ulist = re.search(r'<ul class="ri_ul hots1">(.*?)</ul>', result, re.S)
    # get movie list
    movies = re.findall(r'<a href="(.*?)" title="(.*?)"', ulist.group(1), re.S)

    menus = []
    # 0 is url, 1 is title
    for seq, m in enumerate(movies):
        menus.append({
            'label': '{0}. {1}'.format(seq+1, m[1]),
            'path': plugin.url_for('showmovie', url=m[0],name=m[1]),
        })

    epcache['hot'] = menus
    return menus

@plugin.route('/searchvideo')
def searchvideo():
    """
    search video
    """
    kb = Keyboard('', u'请输入搜索关键字')
    kb.doModal()
    if not kb.isConfirmed():
        return
    sstr = kb.getText()
    if not sstr:
        return
    url = '/index.php?mod=content&action=search&keyword='
    keyword = urllib2.quote(sstr.decode('utf-8').encode('gbk'))
    return showlist(url+keyword)

@plugin.route('/showlist/<url>')
def showlist(url):
    """
    show movie list
    """
    if url in epcache:
        return epcache[url]

    result = _http(baseurl+url)

    ulist = re.search(r'<ul class="list_ul">(.*?)</ul>', result, re.S)
    # get movie list
    movies = re.findall(r'<li><a href="(.*?)" class="tu_a" title="(.*?)"><img src="(.*?)".*?<p>(.*?)</p></li>', ulist.group(1), re.S)

    menus = []
    # 0 is url, 1 is title, 2 is thumbnail, 3 is author
    for seq, m in enumerate(movies):
        menus.append({
            'label': '{0}. {1}【{2}】'.format(seq+1, m[1], m[3]),
            'path': plugin.url_for('showmovie', url=m[0],name=m[1]),
            'thumbnail': m[2],
        })
    # add current/total page number

    pagenum = re.search(r'<div class="page"><ul>(.*?)</ul>', result, re.S)
    if pagenum:
   	cur = re.search(r'<li class="active">(.*?)</li>',pagenum.group(1))
   	total = re.search(r'<li class="home" ><a href="#" style="width:100px">(.*?)</a></li>',pagenum.group(1))
        if cur and total:
            menus.append({
            'label': '[COLOR FFFF0000]第'+cur.group(1)+'页/[/COLOR]'+total.group(1)
            })

        # add pre/next item
        pre = re.search(r'<li class="previous"><a href="(.*?)">(.*?)</a></li>',pagenum.group(1))
        if pre:
            menus.append({
            'label': pre.group(2),
            'path': plugin.url_for('showlist', url=pre.group(1)),
            })

        nex = re.search(r'<li class="next"><a href="(.*?)">(.*?)</a></li>',pagenum.group(1))
        if nex:
            menus.append({
            'label': nex.group(2),
            'path': plugin.url_for('showlist', url=nex.group(1)),
            })
    
    epcache[url] = menus
    return menus

@plugin.route('/showmovie/<url>/<name>')
def showmovie(url,name=''):
    """
    show episodes list
    """
    if url in epcache:
       return epcache[url] 
    urlid= re.search(r'movie/(\d+).html',url)
    movurl='/index.php?mod=api&action=getPlayUrl&movid='+urlid.group(1)+'&urlid=0'
    result = _http(baseurl+movurl)

    molist = re.findall(r'<a href="(.*?)".*?>(.*?)</a>',result)

    menus=[]
    for seq, m in enumerate(molist):
        menus.append({
            'label': '{0}. {1}'.format(seq+1, m[-1]),
            'path': plugin.url_for('playmovie', url=m[0],vname=name+':'+m[-1]),
        })

    # xbmcswift only support thumbnail view mode
    #xbmc.executebuiltin('Container.SetViewMode(503)')
    epcache[url] = menus

    return menus

@plugin.route('/play/<url>/<vname>')
def playmovie(url,vname=''):
    """
    play movie
    """
    result = _http(baseurl+url)

    rtmpstr=re.search(r'var rtmpURL="(rtmp://.*?/.*?)/(.*?\.mp4)"',result,re.S)
    if rtmpstr:
	playurl= rtmpstr.group(1)+' playpath=mp4:'+rtmpstr.group(2)
        item =  {
        'label': vname,
        'path': playurl,
	'is_playable':True
        }
        plugin.play_video(item) 
	#listitem = xbmcgui.ListItem()
        #listitem.setInfo(type="Video", infoLabels={'Title': 'c'})
        #xbmc.Player().play(playurl, listitem)

	#plugin.set_resolved_url(playurl)

@plugin.route('/clscache')
def clscache():
    epcache.clear()
    xbmcgui.Dialog().ok(
        '提示框', '清除成功')
    return


def _http(url):
    """
    open url
    """
    req = urllib2.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) {0}{1}'.
                   format('AppleWebKit/537.36 (KHTML, like Gecko) ',
                          'Chrome/28.0.1500.71 Safari/537.36'))
    req.add_header('Accept-encoding', 'gzip')
    rsp = urllib2.urlopen(req, timeout=30)
    if rsp.info().get('Content-Encoding') == 'gzip':
        buf = StringIO(rsp.read())
        f = gzip.GzipFile(fileobj=buf)
        data = f.read()
    else:
        data = rsp.read()
    rsp.close()

    selfjump=re.search(r'self.location="(.*?)"',data,re.S)
    if selfjump:
	return _http(url+selfjump.group(1))

    match = re.compile(r'<meta content="text/html;[\s]?charset=(.+?)"').findall(data)

    charset='gb2312'
    if len(match)>0:
        charset = match[0]

    if charset:
        charset = charset.lower()

        if (charset != 'utf-8') and (charset != 'utf8'):
            data = data.decode(charset, 'ignore').encode('utf8', 'ignore')
    return data

if __name__ == '__main__':
    plugin.run()
