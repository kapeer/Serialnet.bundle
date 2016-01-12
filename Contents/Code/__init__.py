# -*- coding: utf-8 -*-
const = SharedCodeService.constants
tvdb = SharedCodeService.tvdbapi

ART = 'fanart.jpg'
ICON = 'icon.png'
NAME = L('NAME')
main_url = const.main_url
thumbs_url = const.thumbs_url
watch_url = const.watch_url

def Start():
    Plugin.AddPrefixHandler("/video/serialnet",MainMenu,NAME,ICON,ART)
    Plugin.AddViewGroup("List", viewMode = "List", mediaType = "items")
    Plugin.AddViewGroup('Details', viewMode='InfoList', mediaType='items')
    ObjectContainer.art = R(ART)
    ObjectContainer.title1 = NAME
    ObjectContainer.view_group = "List"
    DirectoryObject.thumb = R(ICON)

   
def MainMenu():
    oc = ObjectContainer()
    oc.no_cache = True
    #Dict['shows'] = {}
    oc.add(DirectoryObject(key=Callback(GetShows,query='all'),title=L('MENU_ALL_SHOWS')))
    oc.add(InputDirectoryObject(key=Callback(GetShows),title=L('MENU_SEARCH'),prompt=L('MESSAGE_SEARCH')))
    #Dict.Reset()
    if Dict['fav']['shows']:
        oc.add(DirectoryObject(key=Callback(ShowFav),title=L('MENU_FAV_SHOWS')))
    #Log(Dict['recent'])
    #if Dict['recent']:
    #    oc.add(DirectoryObject(key=Callback(ShowRecent),title=L('MENU_RECENT')))
    #oc.add(DirectoryObject(key=Callback(TvDbTest),title='TVDB Test'))
    oc.add(PrefsObject(title=L("STRING_SETTINGS")))
    return oc
    
    
@route('/video/serialnet/get',query = str)
def GetShows(query=''):
    try:
        page = HTML.ElementFromURL(main_url,errors='replace',encoding='utf-8',timeout=90,cacheTime=3600*12)
    except:
        Log('Failed to retrieve list of series from url={}'.format(main_url))
        return MessageContainer('ERROR', L('ERROR_NO_SHOWS'))
    else:
        oc = ObjectContainer()
        oc.view_group = "List"
        for item in page.body.iter():
            if "list" in str(item.get('id')):
                for li in item.iterfind('li'):
                    for itag in li.getchildren():
                            if itag.get('href') is not None:
                                url = itag.get('href')
                                title = itag.text
                                thumb = None
                                rating_key = unicode(url.split('/')[-1])
                                if rating_key not in Dict["shows"]:
                                    Dict["shows"][rating_key] = {}
                                Dict["shows"][rating_key]["url"] = url
                                Dict["shows"][rating_key]["title"] = title
                                if "thumb" in Dict["shows"][rating_key]:
                                    thumb = Dict["shows"][rating_key]["thumb"]
                                bAdd = False
                                if query != 'all':
                                    oc.title2 = L('MESSAGE_SEARCH')
                                    if query.lower() in title.lower():
                                        bAdd = True
                                else:
                                    oc.title2 = L('MESSAGE_ALL')
                                    bAdd = True

                                if bAdd:
                                    oc.add(
                                        TVShowObject(
                                            key=Callback(GetSeasons,show=rating_key),
                                            title=title,
                                            rating_key=rating_key,
                                            thumb=thumb
                                        )
                                    )
        return oc


@route('/video/serialnet/all/{show}')
def GetSeasons(show):
    url = Dict["shows"][show]["url"]
    try:
        page = HTML.ElementFromURL(url,errors='replace',encoding='utf-8',timeout=90,cacheTime=60*30)
    except:
        Log('Failed to retrieve list of seasons from url={}'.format(url))
        return MessageContainer('ERROR',L('ERROR_NO_SEASONS'))
    else:
        Dict["shows"][show]["s"] = {}
        oc = ObjectContainer()
        oc.no_cache = True
        oc.view_group = "Details"
        thumb = None
        iNum = 0
        for item in page.body.iter():
            if "desc" in str(item.get('id')):
                for descTag in item.getchildren():
                    if descTag.tag == 'img':
                        thumb = descTag.get('src')
                        Dict["shows"][show]["thumb"] = thumb
                    if descTag.tag == 'strong':
                        summary = unicode(descTag.text)
                    if descTag.tag == 'h2':
                        title = unicode(descTag.text)
            elif "wrp1" in str(item.get('id')):
                episodeTitle = None
                episodeUrl = None
                episodeTitleFull = None
                seasonText = None
                for showTag in item.getchildren():
                    if showTag.tag == 'div':
                        for seasonTag in showTag.getchildren():
                            if seasonTag.tag == 'h3':
                                seasonText = seasonTag.text
                                iSeason = int(seasonText.replace('Sezon','').strip())
                                if iSeason not in Dict["shows"][show]["s"]:
                                    Dict["shows"][show]["s"][iSeason] = {}
                                Dict["shows"][show]["s"][iSeason]["e"] = {}
                    if showTag.tag == 'a':
                        episodeTitleFull = showTag.getchildren()[0].text
                        iEpisode = int(episodeTitleFull.split(' ')[1])
                        if iEpisode not in Dict["shows"][show]["s"][iSeason]["e"]:
                            Dict["shows"][show]["s"][iSeason]["e"][iEpisode] = {}
                        Dict["shows"][show]["s"][iSeason]["e"][iEpisode]["url"] = showTag.get('href')
                        Dict["shows"][show]["s"][iSeason]["e"][iEpisode]["title"] = unicode(showTag.get('title'))
        
        for iSeason in sorted(Dict["shows"][show]["s"],reverse=True):
            rating_key = "{}s{}".format(show,str(iSeason).zfill(2))
            title = str(L("STRING_SEASON")).format(iSeason)
            #summary = str(L("{} Episodes")).format(len(Dict["shows"][show]["s"][iSeason]["e"]))
            oc.add(
                #SeasonObject(
                DirectoryObject(
                    key = Callback(GetEpisodes,show=show,season=iSeason),
                    #rating_key = rating_key,
                    #show = Dict["shows"][show]["title"],
                    #index = iSeason,
                    #episode_count = len(Dict["shows"][show]["s"][iSeason]["e"])
                    title = title
                )
            )
        oc.title2 = Dict["shows"][show]["title"]

        if unicode(show) in Dict['fav']['shows']:
            oc.add(DirectoryObject(key=Callback(DelFromFav,item=show,itemType='shows'),title=L('SUBMENU_DEL_FAV')))
        else:
            oc.add(DirectoryObject(key=Callback(AddToFav,item=show,itemType='shows'),title=L('SUBMENU_ADD_FAV')))
        return oc


@route('/video/serialnet/info/{show}/{season}')
def GetEpisodes(show,season,content='default'):
    duration = None
    fanart = None
    dSeason = Dict["shows"][show]["s"][int(season)]
    
    lOrdered = sorted(dSeason["e"],reverse=True)
    if content == 'default':
        iEpisodesFrom = lOrdered[0]
        if len(lOrdered) > int(Prefs['episodesPerPage']):
            iEpisodesTo = lOrdered[int(Prefs['episodesPerPage']) - 1]
        else:
            iEpisodesTo = lOrdered[-1]
    else:
        iEpisodesFrom = int(content.split('-')[0])
        iEpisodesTo = int(content.split('-')[1])
    
    if bool(Prefs['useTvdb']):
        #Get info from thetvdb api
        Log("Using tvdb API to extract series id")
        try:
            seriesId = tvdb.GetSeriesId(Dict["shows"][show]["title"])
        except:
            Log('Failed to retrieve series information from thetvdb.com')
        else:
            Log("Using tvdb API to extract series data for seriesId={}".format(seriesId))
            try:
                seriesXml = tvdb.GetSeriesData(seriesId)
            except:
                Log("Failed to retrieve series data for seriesId={}".format(seriesId))
            else:
                #actors = tvdb.GetSeriesActors(seriesXml)
                #network = tvdb.GetSeriesNetwork(seriesXml)
                duration = tvdb.GetSeriesDuration(seriesXml)
                fanart = tvdb.GetSeriesFanart(seriesXml)
                episodes = tvdb.GetSeriesEpisodes(seriesXml)
                for episode in episodes:
                    episodeNum = tvdb.GetEpisodeNumber(episode)
                    seasonNum = tvdb.GetSeasonNumber(episode)
                    absoluteNumber = tvdb.GetEpisodeAbsoluteNumber(episode)
                    absoluteCombined = tvdb.GetEpisodeCombinedEpisodeNumber(episode)
                    if absoluteNumber:
                        pass
                    elif absoluteCombined:
                        absoluteNumber = absoluteCombined
                    else:
                        absoluteNumber = 0
                    img = tvdb.GetEpisodeImg(episode)
                    #directors = tvdb.GetEpisodeDirectors(episode)
                    #writers = tvdb.GetEpisodeWriters(episode)
                    firstAired = tvdb.GetEpisodeFirstAired(episode)
                    overview = tvdb.GetEpisodeSummary(episode)
                    episodeNameTVDB = tvdb.GetEpisodeName(episode)
                    bAlt = False
                    if int(episodeNum) <= iEpisodesFrom and int(episodeNum) >= iEpisodesTo: #direct match
                        if int(seasonNum) in Dict["shows"][show]["s"]:
                            if int(episodeNum) in Dict["shows"][show]["s"][int(seasonNum)]["e"]:
                                Dict["shows"][show]["s"][int(seasonNum)]["e"][int(episodeNum)]["thumb"] = img
                                Dict["shows"][show]["s"][int(seasonNum)]["e"][int(episodeNum)]["firstAired"] = firstAired
                                Dict["shows"][show]["s"][int(seasonNum)]["e"][int(episodeNum)]["summary"] = overview
                                Dict["shows"][show]["s"][int(seasonNum)]["e"][int(episodeNum)]["episodeName"] = episodeNameTVDB
                            else:
                                bAlt = True
                        else:
                            bAlt = True
                    elif int(absoluteNumber) <= iEpisodesFrom and int(absoluteNumber) >= iEpisodesTo:
                        bAlt = True
                                                    
                    if bAlt: #try matching episode by absolute value
                        Log('Attempting to match episode by absoluteNumber={}'.format(absoluteNumber))
                        if int(absoluteNumber) in Dict["shows"][show]["s"][1]["e"]:
                            Dict["shows"][show]["s"][1]["e"][int(absoluteNumber)]["thumb"] = img
                            Dict["shows"][show]["s"][1]["e"][int(absoluteNumber)]["firstAired"] = firstAired
                            Dict["shows"][show]["s"][1]["e"][int(absoluteNumber)]["summary"] = overview
                            Dict["shows"][show]["s"][1]["e"][int(absoluteNumber)]["episodeName"] = episodeNameTVDB
    
    oc = ObjectContainer()
    oc.no_cache = True
    oc.view_group = "Details"
    #oc.view_group = "List"
        
    l = []
        
    for iEpisode in lOrdered:
        if iEpisode <= iEpisodesFrom and iEpisode >= iEpisodesTo:
            if "episodeName" in dSeason["e"][iEpisode]:
                if 'dcinek' not in dSeason["e"][iEpisode]["episodeName"]:
                    episodeTitle = dSeason["e"][iEpisode]["episodeName"]
                else:
                    episodeTitle = dSeason["e"][iEpisode]["title"]
            else:
                episodeTitle = dSeason["e"][iEpisode]["title"]
            thumb = None
            art = None
            summary = None
            if "thumb" in dSeason["e"][iEpisode]:
                if dSeason["e"][iEpisode]["thumb"]:
                    thumb = dSeason["e"][iEpisode]["thumb"]
            if fanart:
                art = fanart
            if "summary" in dSeason["e"][iEpisode]:
                summary = dSeason["e"][iEpisode]["summary"]
            #if duration:
            #    duration = int(int(duration)*60000)
            title=str(L("STRING_EPISODE")).format(iEpisode)
            
            if episodeTitle not in title:
                title += ': ' + episodeTitle
                
            Log('Adding episode url={}, show={}, title={}, art={}, thumb={}'.format(dSeason["e"][iEpisode]["url"],Dict["shows"][show]["title"],title,art,thumb))
            oc.add(
                EpisodeObject(
                    url = dSeason["e"][iEpisode]["url"],
                    show = Dict["shows"][show]["title"],
                    summary = summary,
                    art = art,
                    title = title,
                    #duration = duration,
                    thumb = thumb,
                )
            )
        else:
            l.append(iEpisode)
            if len(l) == int(Prefs['episodesPerPage']) or lOrdered[-1] in l:
                oc.add(
                    DirectoryObject(
                        key=Callback(GetEpisodes,show=show,season=season,content='{}-{}'.format(l[0],l[-1])),
                        #rating_key='{}s{}e{}-{}'.format(show,season,l[0],l[-1]),
                        title=str(L('STRING_EPISODE_RANGE')).format(l[0],l[-1]) if len(l) > 1 else str(L('STRING_EPISODE')).format(l[0])
                    )
                )
                l = []
    oc.title2 = Dict["shows"][show]["title"] + ' - ' + str(L("STRING_SEASON")).format(season)
    return oc
    

@route('/video/serialnet/fav/add/{item}')
def AddToFav(item,itemType):
    if unicode(item) not in Dict['fav'][itemType]:
        Dict['fav'][itemType].append(unicode(item))
        Log('{} added to favourite {}'.format(item,itemType))
    else:
        Log('{} already in favourite {}'.format(item,itemType))
    Dict.Save()
    Log(Dict['fav'])
    return MessageContainer('INFO',L('MESSAGE_ADDED'))


@route('/video/serialnet/fav/del/{item}')
def DelFromFav(item,itemType):
    Log(Dict['fav'][itemType].index(item))
    if unicode(item) in Dict['fav'][itemType]:
        Dict['fav'][itemType].remove(unicode(item))
        Log('{} removed from favourite {}'.format(item,itemType))
    else:
        Log('{} already removed from favourite {}'.format(item,itemType))
    Dict.Save()
    Log(Dict['fav'])
    return MessageContainer('INFO',L('MESSAGE_REMOVED'))


@route('/video/serialnet/fav')
def ShowFav():
    oc = ObjectContainer()
    oc.no_cache = True
    Log(Dict['fav'])
    for item in sorted(Dict['fav']['shows']):
        oc.add(DirectoryObject(key=Callback(GetSeasons,show=item),title=Dict["shows"][unicode(item)]["title"]))
    oc.title2 = L('STRING_FAVOURITES')
    return oc


@route('/video/serialnet/recent')
def ShowRecent():
    oc = ObjectContainer()
    oc.no_cache = True
    for item in Dict['recent']:
        oc.add(DirectoryObject(key=Callback(DoNothing),title=item))


def DoNothing():
    return

