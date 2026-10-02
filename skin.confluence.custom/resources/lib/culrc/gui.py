#-*- coding: UTF-8 -*-
# Derived from CU LRC Lyrics 6.7.1.2 (Taxigps, ronie), GPL-2.0.
# JJS integration: embedded popup-only runtime for Confluence Custom, 2026-09-23.
import threading
import time
from threading import Timer
from culrc.utils import *
from culrc.embedlrc import *


JJS_POPUP_PROP = 'ConfluenceCustom.SongSelector.PopupOpen'
JJS_STATUS_PROP = 'culrc.jjsstatus'


def _visualisation_visible():
    return xbmc.getCondVisibility('Window.IsVisible(12006)')


def _jjs_popup_visible():
    # JJS Music Library Manager / Confluence Custom song popup. The Home
    # property is set before ActivateWindow(), so the lyrics service may start
    # fetching immediately without opening CU LRC's own modal GUI.
    return WIN.getProperty(JJS_POPUP_PROP) == '1'


class MAIN():
    def __init__(self):
        WIN.setProperty('culrc.running', 'true')
        self.get_settings()
        log('started as service: %s' % str(self.SETTING_SERVICE), debug=self.DEBUG)
        self.setup_main()
        self.main_loop()
        self.cleanup_main()

    def setup_main(self):
        self.fetchedLyrics = []
        self.current_lyrics = Lyrics(settings=self.lyricssettings)
        self.player_change_pending = True
        self.MyPlayer = MyPlayer(function=self.player_changed, clear=self.clear)
        self.Monitor = MyMonitor(function=self.update_settings)
        self.dialog = xbmcgui.Dialog()
        self.customtimer = False
        self.starttime = 0
        self.CULRC_QUIT = False
        self.CULRC_FIRSTRUN = False
        self.CULRC_NEWLYRICS = False
        self.CULRC_NOLYRICS = False

    def cleanup_main(self):
        # Clean up the monitor and Player classes on exit
        del self.MyPlayer
        del self.Monitor

    def get_settings(self):
        # Embedded JJS mode: preserve the proven CU LRC 6.7.1.2 search order
        # and default providers, but keep configuration and cache inside the skin.
        # There is deliberately no separate CU LRC add-on/settings dependency.
        self.DEBUG = False
        self.SETTING_OFFSET = 0.0
        self.SETTING_SAVE_LYRICS1LRC = True
        self.SETTING_SAVE_LYRICS1TXT = True
        self.SETTING_SAVE_LYRICS2LRC = False
        self.SETTING_SAVE_LYRICS2TXT = False
        self.SETTING_SEARCH_EMBEDDED = True
        self.SETTING_SEARCH_LRC_FILE = True
        self.SETTING_SEARCH_TXT_FILE = True
        self.SETTING_SERVICE = True
        self.SETTING_SILENT = True
        self.SETTING_STRIP = False
        self.SETTING_READ_FILENAME = False
        self.SETTING_READ_FILENAME_FORMAT = 0
        self.SETTING_SAVE_FILENAME_FORMAT = 0
        self.SETTING_SAVE_LYRICS_PATH = os.path.join(PROFILE, 'lyrics')
        self.SETTING_SAVE_SUBFOLDER = False
        self.SETTING_SAVE_SUBFOLDER_PATH = 'lyrics'
        self.SETTING_CLEAN_TITLE = False
        self.SETTING_INTERNETRADIO = False
        self.lyricssettings = {
            'debug': self.DEBUG,
            'read_filename': self.SETTING_READ_FILENAME,
            'read_filename_format': self.SETTING_READ_FILENAME_FORMAT,
            'save_filename_format': self.SETTING_SAVE_FILENAME_FORMAT,
            'save_lyrics_path': self.SETTING_SAVE_LYRICS_PATH,
            'save_subfolder': self.SETTING_SAVE_SUBFOLDER,
            'save_subfolder_path': self.SETTING_SAVE_SUBFOLDER_PATH,
            'clean_title': self.SETTING_CLEAN_TITLE,
        }
        enabled = {
            'musixmatchlrc', 'lrclib', 'music163', 'rclyricsband', 'megalobiz',
            'genius', 'musixmatch', 'lyricsmode', 'azlyrics', 'lyricscom',
            'supermusic', 'darklyrics',
        }
        self.scrapers = []
        for scraper in os.listdir(LYRIC_SCRAPER_DIR):
            if (scraper in enabled and scraper != '__pycache__'
                    and os.path.isdir(os.path.join(LYRIC_SCRAPER_DIR, scraper))):
                exec('from culrc.culrcscrapers.%s import lyricsScraper as lyricsScraper_%s' % (scraper, scraper), globals())
                exec('self.scrapers.append([lyricsScraper_%s.__priority__, lyricsScraper_%s.LyricsFetcher(debug=self.DEBUG, settings=self.lyricssettings), lyricsScraper_%s.__title__, lyricsScraper_%s.__lrc__])'
                     % (scraper, scraper, scraper, scraper))
        self.scrapers.sort()
        if not xbmcvfs.exists(self.SETTING_SAVE_LYRICS_PATH):
            try:
                xbmcvfs.mkdirs(self.SETTING_SAVE_LYRICS_PATH)
            except Exception:
                pass
        WIN.clearProperty('culrc.hidedialog')

    def main_loop(self):
        # main loop
        while (not self.Monitor.abortRequested()) and (not self.CULRC_QUIT):
            # JJS mode searches only for the Confluence Custom song popup.
            # Full-screen music visualisation is deliberately not a lyrics context.
            if self.proceed():
                if not self.CULRC_FIRSTRUN:
                    self.CULRC_FIRSTRUN = True
                    self.player_change_pending = True
                    if not self.SETTING_SILENT and _visualisation_visible():
                        self.dialog.notification(ADDONNAME, LANGUAGE(32004), icon=ADDONICON, time=2000, sound=False)
                if WIN.getProperty('culrc.force') == 'TRUE':
                    WIN.setProperty('culrc.force','FALSE')
                    self.current_lyrics = Lyrics(settings=self.lyricssettings)
                    self.player_change_pending = True
                # onAVStarted only marks work pending. Network/scraper work is
                # deliberately executed here, after the Kodi player callback has returned.
                if self.player_change_pending:
                    self.player_change_pending = False
                    self.myPlayerChanged()
                elif xbmc.getCondVisibility('Player.IsInternetStream') and self.SETTING_INTERNETRADIO:
                    self.myPlayerChanged()
            else:
                # The external popup has closed. Reset current lyrics so a later
                # popup session starts a fresh per-track search/publication cycle.
                if self.CULRC_FIRSTRUN:
                    self.current_lyrics = Lyrics(settings=self.lyricssettings)
                self.CULRC_FIRSTRUN = False
                self.player_change_pending = False
                if not _jjs_popup_visible():
                    WIN.clearProperty(JJS_STATUS_PROP)
            xbmc.sleep(100)
        WIN.clearProperty('culrc.lyrics')
        WIN.clearProperty('culrc.islrc')
        WIN.clearProperty('culrc.source')
        WIN.clearProperty('culrc.haslist')
        WIN.clearProperty('culrc.running')
        WIN.clearProperty('culrc.hidedialog')
        WIN.clearProperty(JJS_STATUS_PROP)

    def get_lyrics(self, song, prefetch):
        log('searching memory for lyrics', debug=self.DEBUG)
        lyrics = self.get_lyrics_from_memory(song)
        if lyrics:
            if lyrics.lyrics:
                log('found lyrics in memory', debug=self.DEBUG)
            else:
                log('no lyrics found on previous search', debug=self.DEBUG)
            return lyrics
        # searching lyrics for the current song and no pre-fetched lyrics available, hide the gui
        if not prefetch:
            self.CULRC_NOLYRICS = True
        if song.title and self.proceed():
            lyrics = self.find_lyrics(song)

            # JJS fallback: preserve the exact Kodi title as the first search.
            # Only when that complete search returns nothing, retry once without
            # one trailing parenthesized suffix such as "(Live)" or
            # "(Remastered 2025)". The displayed/tagged title is never changed.
            if not lyrics.lyrics and self.proceed():
                cleaned_title = re.sub(r'\s*\([^()]*\)\s*$', '', song.title).strip()
                if cleaned_title and cleaned_title != song.title:
                    retry_song = Song(opt=self.lyricssettings)
                    retry_song.artist = song.artist
                    retry_song.title = cleaned_title
                    retry_song.filepath = song.filepath
                    retry_song.embed = song.embed
                    retry_song.source = song.source
                    retry_song.analyze_safe = song.analyze_safe
                    log(
                        'no lyrics for exact title; retrying without trailing parentheses: %s'
                        % cleaned_title,
                        debug=self.DEBUG,
                    )
                    retry_lyrics = self.find_lyrics(retry_song)
                    if retry_lyrics.lyrics:
                        retry_lyrics.song = song
                        lyrics = retry_lyrics

            if lyrics.lyrics and self.SETTING_STRIP:
                # replace CJK and fullwith colon (not present in many font files)
                lyrics.lyrics = re.sub(r'[ᄀ-ᇿ⺀-⺙⺛-⻳⼀-⿕々〇〡-〩〸-〺〻㐀-䶵一-鿃豈-鶴侮-頻並-龎]+', '', lyrics.lyrics).replace('：',':') 
        # no song title, we can't search online. try matching local filename
        elif (self.SETTING_SAVE_LYRICS2LRC or self.SETTING_SAVE_LYRICS2TXT) and self.proceed():
            lyrics = self.get_lyrics_from_file(song, True)
            if not lyrics:
                lyrics = self.get_lyrics_from_file(song, False)
        if not lyrics:
            lyrics = Lyrics(settings=self.lyricssettings)
            lyrics.song = song
            lyrics.source = ''
            lyrics.lyrics = ''
        if self.proceed():
            self.save_lyrics_to_memory(lyrics)
        return lyrics

    def find_lyrics(self, song):
        # search embedded lrc lyrics
        if self.SETTING_SEARCH_EMBEDDED and self.proceed(): # Add embedded lyrics for internet streams
            log('searching for embedded lrc lyrics', debug=self.DEBUG)
            try:
                lyrics = getEmbedLyrics(song, True, self.lyricssettings)
            except:
                lyrics = None
            if (lyrics):
                log('found embedded lrc lyrics', debug=self.DEBUG)
                return lyrics
        # search lrc lyrics from file
        if self.SETTING_SEARCH_LRC_FILE and self.proceed():
            log('searching for local lrc files', debug=self.DEBUG)
            lyrics = self.get_lyrics_from_file(song, True)
            if (lyrics):
                log('found lrc lyrics from file', debug=self.DEBUG)
                return lyrics
        # search lrc lyrics by scrapers
        for scraper in self.scrapers:
            if scraper[3] and self.proceed():
                try:
                    lyrics = scraper[1].get_lyrics(song)
                except Exception as exc:
                    # A broken provider must never terminate the complete lyrics
                    # service; continue with the remaining configured scrapers.
                    log('scraper %s failed: %s' % (scraper[2], exc), debug=self.DEBUG)
                    lyrics = None
                if (lyrics):
                    log('found lrc lyrics online', debug=self.DEBUG)
                    self.save_lyrics_to_file(lyrics)
                    return lyrics
        # search embedded txt lyrics
        if self.SETTING_SEARCH_EMBEDDED and self.proceed(): # Add embedded lyrics for internet streams
            log('searching for embedded txt lyrics', debug=self.DEBUG)
            try:
                lyrics = getEmbedLyrics(song, False, self.lyricssettings)
            except:
                lyrics = None
            if lyrics:
                log('found embedded txt lyrics', debug=self.DEBUG)
                return lyrics
        # search txt lyrics from file
        if self.SETTING_SEARCH_TXT_FILE and self.proceed():
            log('searching for local txt files', debug=self.DEBUG)
            lyrics = self.get_lyrics_from_file(song, False)
            if (lyrics):
                log('found txt lyrics from file', debug=self.DEBUG)
                return lyrics
        # search txt lyrics by scrapers
        for scraper in self.scrapers:
            if not scraper[3] and self.proceed():
                try:
                    lyrics = scraper[1].get_lyrics(song)
                except Exception as exc:
                    log('scraper %s failed: %s' % (scraper[2], exc), debug=self.DEBUG)
                    lyrics = None
                if (lyrics):
                    log('found txt lyrics online', debug=self.DEBUG)
                    self.save_lyrics_to_file(lyrics)
                    return lyrics
        log('no lyrics found', debug=self.DEBUG)
        lyrics = Lyrics(settings=self.lyricssettings)
        lyrics.song = song
        lyrics.source = ''
        lyrics.lyrics = ''
        return lyrics

    def get_lyrics_from_memory(self, song):
        for l in self.fetchedLyrics:
            if (l.song == song):
                return l
        return None

    def get_lyrics_from_file(self, song, getlrc):
        lyrics = Lyrics(settings=self.lyricssettings)
        lyrics.song = song
        lyrics.source = LANGUAGE(32000)
        lyrics.lrc = getlrc
        if self.SETTING_SAVE_LYRICS1LRC or self.SETTING_SAVE_LYRICS1TXT:
            # Search save path by Cu LRC Lyrics
            lyricsfile = song.path1(getlrc)
            log('path1: %s' % lyricsfile, debug=self.DEBUG)
            if xbmcvfs.exists(lyricsfile):
                lyr = get_textfile(lyricsfile)
                if lyr != None:
                    lyrics.lyrics = lyr
                    return lyrics
        if self.SETTING_SAVE_LYRICS2LRC or self.SETTING_SAVE_LYRICS2TXT:
            # Search same path with song file
            lyricsfile = song.path2(getlrc)
            log('path2: %s' % lyricsfile, debug=self.DEBUG)
            # don't search online sources for saved lyrics files
            if xbmc.getCondVisibility('Player.IsInternetStream') or xbmc.getCondVisibility('Pvr.IsPlayingRadio'):
                return None
            if xbmcvfs.exists(lyricsfile):
                lyr = get_textfile(lyricsfile)
                if lyr != None:
                    lyrics.lyrics = lyr
                    return lyrics
        return None

    def save_lyrics_to_memory(self, lyrics):
        savedLyrics = self.get_lyrics_from_memory(lyrics.song)
        if (savedLyrics is None):
            self.fetchedLyrics.append(lyrics)
            self.fetchedLyrics = self.fetchedLyrics[-10:]

    def save_lyrics_to_file(self, lyrics, adjust=None):
        if isinstance (lyrics.lyrics, str):
            lyr = lyrics.lyrics
        else:
            lyr = lyrics.lyrics
        if adjust:
            # save our manual sync offset to file
            adjust = int(adjust * 1000)
            # check if there's an existing offset tag
            found = re.search(r'\[offset:(.*?)\]', lyr, flags=re.DOTALL)
            if found:
                # get the sum of both values
                try:
                    adjust = int(found.group(1)) + adjust
                except:
                    # offset tag without value
                    pass
                # remove the existing offset tag
                lyr = lyr.replace(found.group(0) + '\n','')
            # write our new offset tag
            lyr = '[offset:%i]\n' % adjust + lyr
        if (self.SETTING_SAVE_LYRICS1LRC and lyrics.lrc) or (self.SETTING_SAVE_LYRICS1TXT and not lyrics.lrc):
            file_path = lyrics.song.path1(lyrics.lrc)
            success = self.write_lyrics_file(file_path, lyr)
        if (self.SETTING_SAVE_LYRICS2LRC and lyrics.lrc) or (self.SETTING_SAVE_LYRICS2TXT and not lyrics.lrc):
            file_path = lyrics.song.path2(lyrics.lrc)
            success = self.write_lyrics_file(file_path, lyr)

    def write_lyrics_file(self, path, data):
        try:
            if (not xbmcvfs.exists(os.path.dirname(path))):
                xbmcvfs.mkdirs(os.path.dirname(path))
            lyrics_file = xbmcvfs.File(path, 'w')
            lyrics_file.write(data)
            lyrics_file.close()
            return True
        except:
            log('failed to save lyrics', debug=self.DEBUG)
            return False

    def remove_lyrics_from_memory(self, lyrics):
        # delete lyrics from memory
        if lyrics in self.fetchedLyrics:
            self.fetchedLyrics.remove(lyrics)

    def delete_lyrics(self, lyrics):
        # delete lyrics from memory
        self.remove_lyrics_from_memory(lyrics)
        # delete saved lyrics
        if (self.SETTING_SAVE_LYRICS1LRC and lyrics.lrc) or (self.SETTING_SAVE_LYRICS1LRC and not lyrics.lrc):
            file_path = lyrics.song.path1(lyrics.lrc)
            success = self.delete_file(file_path)
        if (self.SETTING_SAVE_LYRICS2LRC and lyrics.lrc) or (self.SETTING_SAVE_LYRICS2LRC and not lyrics.lrc):
            file_path = lyrics.song.path2(lyrics.lrc)
            success = self.delete_file(file_path)

    def delete_file(self, path):
        try:
            xbmcvfs.delete(path)
            return True
        except:
            log('failed to delete file', debug=self.DEBUG)
            return False

    def player_changed(self):
        # Keep Kodi's player callback tiny. The actual search may involve local
        # parsing plus multiple network scrapers and must not run in onAVStarted.
        self.player_change_pending = True

    def myPlayerChanged(self):
        if not self.CULRC_FIRSTRUN:
            return
        global lyrics
        songchanged = False
        for cnt in range(5):
            song = Song.current(opt=self.lyricssettings)
            if song and (self.current_lyrics.song != song):
                songchanged = True
                if xbmc.getCondVisibility('Player.IsInternetStream') and not xbmc.getInfoLabel('MusicPlayer.TimeRemaining'):
                    # internet stream that does not provide time, we need our own timer to sync lrc lyrics
                    self.starttime = time.time()
                    self.customtimer = True
                else:
                    self.customtimer = False
                log('Current Song: %s - %s' % (song.artist, song.title), debug=self.DEBUG)
                if _jjs_popup_visible():
                    # Explicit per-track state for the external popup. This avoids
                    # treating culrc.running as a per-search indicator.
                    WIN.setProperty(JJS_STATUS_PROP, 'searching')
                    WIN.clearProperty('culrc.lyrics')
                    WIN.clearProperty('culrc.source')
                    WIN.clearProperty('culrc.islrc')
                    WIN.clearProperty('culrc.haslist')
                lyrics = self.get_lyrics(song, False)
                self.current_lyrics = lyrics
                # if we have found lyrics and have not skipped to another track while searching for lyrics, show lyrics
                if lyrics.lyrics and (song == Song.current(opt=self.lyricssettings)):
                    # signal the gui thread to display the next lyrics
                    self.CULRC_NOLYRICS = False
                    self.CULRC_NEWLYRICS = True
                    if _jjs_popup_visible():
                        # External consumer: publish the same properties that CU LRC's
                        # GUI normally publishes, but never open the CU LRC dialog.
                        self.publish_jjs_lyrics(lyrics)
                else:
                    # signal gui thread to exit
                    self.CULRC_NOLYRICS = True
                    if _jjs_popup_visible():
                        self.publish_jjs_lyrics(lyrics)
                    elif self.MyPlayer.isPlayingAudio() and not self.SETTING_SILENT and _visualisation_visible():
                        # notify user no lyrics were found
                        self.dialog.notification(ADDONNAME + ': ' + LANGUAGE(32001), song.artist + ' - ' + song.title, icon=ADDONICON, time=2000, sound=False)
                break
            xbmc.sleep(50)
        # No synchronous next-song prefetch here. A slow provider could otherwise
        # occupy this worker across the real track boundary. The next title is
        # searched as soon as onAVStarted marks it pending.

    def update_settings(self):
        self.get_settings()
        if not self.SETTING_SERVICE:
            # quit the script if mode was changed from service to manual
            self.CULRC_QUIT = True

    def callback(self, action):
        if action == 'quit':
            self.CULRC_QUIT = True
        elif action == 'newlyrics':
            if self.CULRC_NEWLYRICS:
                self.CULRC_NEWLYRICS = False
                return True
            return False
        elif action == 'nolyrics':
            return self.CULRC_NOLYRICS

    def publish_jjs_lyrics(self, lyrics):
        if lyrics and lyrics.lyrics:
            WIN.setProperty('culrc.lyrics', lyrics.lyrics)
            WIN.setProperty('culrc.source', lyrics.source or '')
            if lyrics.lrc:
                WIN.setProperty('culrc.islrc', 'true')
            else:
                WIN.clearProperty('culrc.islrc')
            if lyrics.list:
                WIN.setProperty('culrc.haslist', 'true')
            else:
                WIN.clearProperty('culrc.haslist')
            WIN.setProperty(JJS_STATUS_PROP, 'found')
        else:
            WIN.clearProperty('culrc.lyrics')
            WIN.clearProperty('culrc.islrc')
            WIN.clearProperty('culrc.source')
            WIN.clearProperty('culrc.haslist')
            WIN.setProperty(JJS_STATUS_PROP, 'not_found')

    def proceed(self):
        # JJS compatibility mode is intentionally popup-only. The user does not
        # want CU LRC to display lyrics over Kodi's full-screen music visualisation.
        # Search/publish therefore runs only while the Confluence Custom song popup
        # is open; the normal visualisation context is deliberately ignored.
        return _jjs_popup_visible() and not self.Monitor.abortRequested()

    def clear(self):
        WIN.clearProperty('culrc.lyrics')
        WIN.clearProperty('culrc.islrc')
        WIN.clearProperty('culrc.source')
        WIN.clearProperty('culrc.haslist')
        if _jjs_popup_visible():
            WIN.setProperty(JJS_STATUS_PROP, 'searching')
        else:
            WIN.clearProperty(JJS_STATUS_PROP)

    def return_time(self):
        return self.customtimer, self.starttime


class guiThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self)
        self.kwargs = kwargs['opt']

    def run(self):
        ui = GUI('script-cu-lrclyrics-main.xml', CWD, 'Default', opt=self.kwargs)
        ui.doModal()
        del ui
        WIN.clearProperty('culrc.guirunning')


class syncThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self)
        self.function = kwargs['function']
        self.adjust = kwargs['adjust']
        self.save = kwargs['save']
        self.remove = kwargs['remove']
        self.lyrics = kwargs['lyrics']
        self.Monitor = kwargs['monitor']

    def run(self):
        from culrc import sync
        dialog = sync.GUI('DialogSlider.xml' , CWD, 'Default', offset=self.adjust, function=self.function, monitor=self.Monitor)
        dialog.doModal()
        adjust = dialog.val
        del dialog
        # safe new offset to file
        self.save(self.lyrics, adjust)
        # file has changed, remove it from memory
        self.remove(self.lyrics)

class GUI(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self)
        self.save = kwargs['opt']['save']
        self.remove = kwargs['opt']['remove']
        self.delete = kwargs['opt']['delete']
        self.function = kwargs['opt']['function']
        self.callback = kwargs['opt']['callback']
        self.Monitor = kwargs['opt']['monitor']
        self.SETTING_OFFSET = kwargs['opt']['offset']
        self.SETTING_SERVICE = kwargs['opt']['service']
        self.SETTING_STRIP = kwargs['opt']['strip']
        self.DEBUG = kwargs['opt']['debug']
        self.lyricssettings = kwargs['opt']['settings']
        self.dialog = xbmcgui.Dialog()

    def onInit(self):
        self.matchlist = ['@', r'www\.(.*?)\.(.*?)', 'QQ(.*?)[1-9]', 'artist ?: ?.', 'album ?: ?.', 'title ?: ?.', 'song ?: ?.', 'by ?: ?.']
        self.text = self.getControl(110)
        self.label = self.getControl(200)
        self.setup_gui()
        self.process_lyrics()
        # we have processed the lyrics, reset the new lyrics bool, else we do it again when entering the main loop
        self.callback('newlyrics')
        self.gui_loop()

    def process_lyrics(self):
        global lyrics
        self.syncadjust = 0.0
        self.selectedlyric = 0
        self.lyrics = lyrics
        self.stop_refresh()
        self.reset_controls()
        if self.lyrics.lyrics:
            self.show_lyrics(self.lyrics)
        else:
            WIN.setProperty('culrc.lyrics', LANGUAGE(32001))
            WIN.clearProperty('culrc.islrc')

        if self.lyrics.list:
            WIN.setProperty('culrc.haslist', 'true')
            self.prepare_list(self.lyrics.list)
        else:
            WIN.clearProperty('culrc.haslist')
            self.choices = []

    def gui_loop(self):
        # gui loop
        while self.showgui and (not self.Monitor.abortRequested()) and xbmc.Player().isPlayingAudio():
            # check if we have new lyrics
            if self.callback('newlyrics'):
                # show new lyrics
                self.process_lyrics()
            # check if we have no lyrics
            elif self.deleted or self.callback('nolyrics'):
                # no lyrics, close the gui
                self.exit_gui('close')
            elif not xbmc.getCondVisibility('Window.IsVisible(12006)'):
                # we're not on the visualisation screen anymore
                self.exit_gui('quit')
            xbmc.sleep(100)
        # music ended, close the gui
        if (not xbmc.Player().isPlayingAudio()):
            self.exit_gui('quit')
        # xbmc quits, close the gui 
        elif self.Monitor.abortRequested():
            self.exit_gui('quit')

    def setup_gui(self):
        WIN.clearProperty('culrc.haslist')
#        self.lock = threading.Lock()
        self.timer = None
        self.allowtimer = True
        self.refreshing = False
        self.blockOSD = False
        self.controlId = -1
        self.pOverlay = []
        self.choices = []
        self.scroll_line = int(self.get_page_lines() / 2)
        self.showgui = True
        self.deleted = False

    def get_page_lines(self):
        # we need to close the OSD else we can't get control 110
        self.blockOSD = True
        if xbmc.getCondVisibility('Window.IsVisible(musicosd)'):
            xbmc.executebuiltin('Dialog.Close(musicosd,true)')
        self.text.setVisible(False)
        # numpages returns a string, make sure it's not empty
        while xbmc.getInfoLabel('Container(110).NumPages') and (int(xbmc.getInfoLabel('Container(110).NumPages')) < 2) and (not self.Monitor.abortRequested()):
            listitem = xbmcgui.ListItem(offscreen=True)
            self.text.addItem(listitem)
            xbmc.sleep(5)
        # xbmc quits, close the gui 
        if self.Monitor.abortRequested():
            self.exit_gui('quit')
        lines = self.text.size() - 1
        self.blockOSD = False
        return lines

    def refresh(self):
#        self.lock.acquire()
        #Maybe Kodi is not playing any media file
        try:
            customtimer, starttime = self.function()
            if customtimer:
                cur_time = time.time() - starttime
            else:
                cur_time = xbmc.Player().getTime()
            nums = self.text.size()
            pos = self.text.getSelectedPosition()
            if (cur_time < (self.pOverlay[pos][0] - self.syncadjust)):
                while (pos > 0 and (self.pOverlay[pos - 1][0] - self.syncadjust) > cur_time):
                    pos = pos -1
            else:
                while (pos < nums - 1 and (self.pOverlay[pos + 1][0] - self.syncadjust) < cur_time):
                    pos = pos +1
                if (pos + self.scroll_line > nums - 1):
                    self.text.selectItem(nums - 1)
                else:
                    self.text.selectItem(pos + self.scroll_line)
            self.text.selectItem(pos)
            self.setFocus(self.text)
            if (self.allowtimer and cur_time < (self.pOverlay[nums - 1][0] - self.syncadjust)):
                waittime = (self.pOverlay[pos + 1][0] - self.syncadjust) - cur_time
                self.timer = Timer(waittime, self.refresh)
                self.refreshing = True
                self.timer.start()
            else:
                self.refreshing = False
#            self.lock.release()
        except:
            pass
#            self.lock.release()

    def stop_refresh(self):
#        self.lock.acquire()
        try:
            self.timer.cancel()
        except:
            pass
        self.refreshing = False
#        self.lock.release()

    def show_lyrics(self, lyrics):
        WIN.setProperty('culrc.lyrics', lyrics.lyrics)
        WIN.setProperty('culrc.source', lyrics.source)
        if lyrics.list:
            source = '%s (%d)' % (lyrics.source, len(lyrics.list))
        else:
            source = lyrics.source
        self.label.setLabel(source)
        if lyrics.lrc:
            WIN.setProperty('culrc.islrc', 'true')
            self.parser_lyrics(lyrics.lyrics)
            for num, (time, line) in enumerate(self.pOverlay):
                cleanline = line.strip()
                parts = self.get_parts(cleanline)
                listitem = xbmcgui.ListItem(cleanline, offscreen=True)
                for count, item in enumerate(parts):
                    listitem.setProperty('part%i' % (count + 1), item)
                delta = 100000 # in case duration of the last line is undefined
                if num < len(self.pOverlay) - 1:
                    delta = (self.pOverlay[num+1][0] - time) * 1000
                listitem.setProperty('duration', str(int(delta)))
                listitem.setProperty('time', str(time))
                self.text.addItem(listitem)
        else:
            WIN.clearProperty('culrc.islrc')
            splitLyrics = lyrics.lyrics.splitlines()
            for line in splitLyrics:
                cleanline = line.strip()
                parts = self.get_parts(cleanline)
                listitem = xbmcgui.ListItem(cleanline, offscreen=True)
                for count, item in enumerate(parts):
                    listitem.setProperty('part%i' % (count + 1), item)
                self.text.addItem(listitem)
        self.text.selectItem(0)
        self.text.setVisible(True)
        xbmc.sleep(5)
        self.setFocus(self.text)
        if lyrics.lrc:
            if (self.allowtimer and self.text.size() > 1):
                self.refresh()

    def match_pattern(self, line):
        for item in self.matchlist:
            match = re.search(item, line, flags=re.IGNORECASE)
            if match:
                return True

    def get_parts(self, line):
        result = ['', '', '', '']
        parts = line.split(' ', 3)
        for count, item in enumerate(parts):
            result[count] = item
        return result

    def parser_lyrics(self, lyrics):
        offset = 0.00
        found = re.search(r'\[offset:\s?(-?\d+)\]', lyrics)
        if found:
            offset = float(found.group(1)) / 1000
        self.pOverlay = []
        tag1 = re.compile(r'\[(\d+):(\d\d)[\.:](\d\d)\]')
        tag2 = re.compile(r'\[(\d+):(\d\d)([\.:]\d+|)\]')
        lyrics = lyrics.replace('\r\n' , '\n')
        sep = '\n'
        for x in lyrics.split(sep):
            if self.match_pattern(x):
                continue
            match1 = tag1.match(x)
            match2 = tag2.match(x)
            times = []
            if (match1):
                while (match1): # [xx:yy.zz]
                    times.append(float(match1.group(1)) * 60 + float(match1.group(2)) + (float(match1.group(3))/100) + self.SETTING_OFFSET - offset)
                    y = 6 + len(match1.group(1)) + len(match1.group(3))
                    x = x[y:]
                    match1 = tag1.match(x)
                for time in times:
                    self.pOverlay.append((time, x))
            elif (match2): # [xx:yy]
                while (match2):
                    times.append(float(match2.group(1)) * 60 + float(match2.group(2)) + self.SETTING_OFFSET - offset)
                    y = 5 + len(match2.group(1)) + len(match2.group(3))
                    x = x[y:]
                    match2 = tag2.match(x)
                for time in times:
                    self.pOverlay.append((time, x))
        self.pOverlay.sort()
        # don't display/focus the first line from the start of the song
        self.pOverlay.insert(0, (00.00, ''))
        if self.SETTING_STRIP:
            poplist = []
            prev_time = []
            prev_line = ''
            for num, (time, line) in enumerate(self.pOverlay):
                if time == prev_time:
                    if len(line) > len(prev_line):
                        poplist.append(num - 1)
                    else:
                        poplist.append(num)
                prev_time = time
                prev_line = line
            for i in reversed(poplist):
                self.pOverlay.pop(i)

    def prepare_list(self, lyricslist):
        self.choices = []
        for song in lyricslist:
            listitem = xbmcgui.ListItem(song[0], offscreen=True)
            listitem.setProperty('lyric', str(song))
            listitem.setProperty('source', lyrics.source)
            self.choices.append(listitem)

    def reshow_choices(self):
        if self.choices:
            select = self.dialog.select(LANGUAGE(32005), self.choices, preselect=self.selectedlyric)
            if select > -1 and select != self.selectedlyric:
                self.selectedlyric = select
                self.stop_refresh()
                item = self.choices[select]
                source = item.getProperty('source').lower()
                lyric = eval(item.getProperty('lyric'))
                exec ('from culrc.culrcscrapers.%s import lyricsScraper as lyricsScraper_%s' % (source, source))
                scraper = eval('lyricsScraper_%s.LyricsFetcher(debug=self.DEBUG, settings=self.lyricssettings)' % source)
                self.lyrics.lyrics = scraper.get_lyrics_from_list(lyric)
                self.text.reset()
                self.show_lyrics(self.lyrics)
                self.save(self.lyrics)

    def set_synctime(self, adjust):
        self.syncadjust = adjust

    def scrolltosync(self):
        old_time = xbmc.Player().getTime()
        item = self.text.getSelectedItem()
        new_time = float(item.getProperty('time'))
        self.syncadjust = new_time - old_time
        # safe new offset to file
        self.save(self.lyrics, self.syncadjust)
        # file has changed, remove it from memory
        self.remove(self.lyrics)

    def context_menu(self):
        labels = ()
        functions = ()
        if self.choices:
            labels += (LANGUAGE(32006),)
            functions += ('select',)
        if WIN.getProperty('culrc.islrc') == 'true':
            labels += (LANGUAGE(32007),)
            functions += ('sync',)
        if lyrics.source != LANGUAGE(32002):
            labels += (LANGUAGE(32167),)
            functions += ('delete',)
        if labels:
            selection = self.dialog.contextmenu(labels)
            if selection >= 0:
                if functions[selection] == 'select':
                    self.reshow_choices()
                elif functions[selection] == 'sync':
                    sync = syncThread(adjust=self.syncadjust, function=self.set_synctime, save=self.save, lyrics=self.lyrics, remove=self.remove, monitor=self.Monitor)
                    sync.start()
                elif functions[selection] == 'delete':
                    self.lyrics.lyrics = ''
                    self.reset_controls()
                    self.deleted = True
                    self.delete(self.lyrics)

    def reset_controls(self):
        self.text.reset()
        self.label.setLabel('')
        WIN.clearProperty('culrc.lyrics')
        WIN.clearProperty('culrc.islrc')
        WIN.clearProperty('culrc.source')

    def exit_gui(self, action):
        # in manual mode, we also need to quit the script when the user cancels the gui or music has ended
        if (not self.SETTING_SERVICE) and (action == 'quit'):
            # signal the main loop to quit
            self.callback('quit')
        self.allowtimer = False
        self.stop_refresh()
        self.showgui = False
        self.close()

    def onClick(self, controlId):
        if (controlId == 110):
            # will only work for lrc based lyrics
            try:
                item = self.text.getSelectedItem()
                stamp = float(item.getProperty('time'))
                xbmc.Player().seekTime(stamp)
            except:
                pass

    def onFocus(self, controlId):
        self.controlId = controlId

    def onAction(self, action):
        actionId = action.getId()
        if (actionId in CANCEL_DIALOG):
            # dialog cancelled, close the gui
            self.exit_gui('quit')
        elif (actionId == 101) or (actionId == 117): # ACTION_MOUSE_RIGHT_CLICK / ACTION_CONTEXT_MENU
            self.context_menu()
        elif (actionId in ACTION_OSD):
            if not self.blockOSD:
                # mouse move constantly calls ACTION_OSD, process only once
                if not xbmc.getCondVisibility('Window.IsVisible(10120)'):
                    xbmc.executebuiltin('ActivateWindow(10120)')
        elif (actionId in ACTION_CODEC):
            xbmc.executebuiltin('Action(PlayerProcessInfo)')
        elif (actionId in ACTION_UPDOWN) and (self.controlId == 110) and WIN.getProperty('culrc.islrc') == 'true':
            self.scrolltosync()

class MyPlayer(xbmc.Player):
    def __init__(self, *args, **kwargs):
        xbmc.Player.__init__(self)
        self.function = kwargs['function']
        self.clear = kwargs['clear']

    def onAVStarted(self):
        self.clear()
        if _visualisation_visible() or _jjs_popup_visible():
            self.function()

    def onPlayBackStopped(self):
        self.clear()

    def onPlayBackEnded(self):
        self.clear()

class MyMonitor(xbmc.Monitor):
    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)
        self.function = kwargs['function']

    def onSettingsChanged(self):
        # sleep before retrieving the new settings
        xbmc.sleep(500)
        self.function()
