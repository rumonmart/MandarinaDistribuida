#!/usr/bin/python3
# -*- mode:python; coding:utf-8; tab-width:4 -*-
# pylint: disable=import-error
'''Cola de tareas'''
from __future__ import print_function
import os.path
from threading import Thread
from queue import Queue

import youtube_dl

import Ice
# pylint: disable=C0413
Ice.loadSlice('downloader.ice')
# pylint: enable=C0413
# pylint: disable=E0401
import Downloader


class NullLogger:
    '''
    Logger used to disable youtube-dl output
    '''

    def debug(self, msg):
        '''Ignore debug messages'''

    def warning(self, msg):
        '''Ignore warnings'''

    def error(self, msg):
        '''Ignore errors'''

# Default configuration for youtube-dl
DOWNLOADER_OPTS = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'logger': NullLogger()
}


def _download_mp3_(url, destination='./'):
    '''
    Synchronous download from YouTube
    '''
    options = {}
    task_status = {}

    def progress_hook(status):
        '''dowwnload mp3 file and store'''
        task_status.update(status)
    options.update(DOWNLOADER_OPTS)
    options['progress_hooks'] = [progress_hook]
    options['outtmpl'] = os.path.join(destination, '%(title)s.%(ext)s')
    with youtube_dl.YoutubeDL(options) as ydl:
        ydl.download([url])
    filename = task_status['filename']
    # BUG: filename extension is wrong, it must be mp3
    filename = filename[:filename.rindex('.') + 1]
    return filename + options['postprocessors'][0]['preferredcodec']


class WorkQueue(Thread):
    '''Job Queue to dispatch tasks'''
    QUIT = 'QUIT'
    CANCEL = 'CANCEL'
    Progress_Event = None
    queue = None

    def __init__(self, Progress_Event):
        '''Inicialización de la cola de trabajos mediante la cola y el
        evento de progreso'''
        super(WorkQueue, self).__init__()
        self.queue = Queue()
        self.Progress_Event = Progress_Event

    def run(self):
        '''Task dispatcher loop'''
        for job in iter(self.queue.get, self.QUIT):
            job.download()
            self.queue.task_done()

        self.queue.task_done()
        self.queue.put(self.CANCEL)

        for job in iter(self.queue.get, self.CANCEL):
            job.cancel()
            self.queue.task_done()

        self.queue.task_done()

    def add(self, callback, url, songs):
        '''Add new task to queue'''
        self.queue.put(Job(callback, url, self.Progress_Event, songs))

    def destroy(self):
        '''Cancel tasks queue'''
        self.queue.put(self.QUIT)
        self.queue.join()

    def destroy_job(self, url):
        '''Cancela una descarga dada una url'''
        for job in iter(self.queue.get, None):
            print('song '+str(job.url))
            if job.url == url:
                self.queue.task_done()
                job.cancel()


class Job(object):
    '''Task: clip to download'''

    def __init__(self, callback, url, Progress_Event, songs):
        '''Inicialización de un trabajo'''
        self.callback = callback
        self.url = url
        self.Progress_Event = Progress_Event
        self.songs = songs
        self.notify_status(Downloader.Status.PENDING)

    def notify_status(self, status):
        '''Notifica un cambio en el estado de la canción'''
        status_data = Downloader.ClipData()
        status_data.URL = self.url
        status_data.status = status
        self.Progress_Event.notify(status_data)

    def download(self):
        '''Descarga una canción, inicialmente notifica como en progreso y cuando
        termina como terminado (visto en clase)'''
        self.notify_status(Downloader.Status.INPROGRESS)
        try:
            filename = _download_mp3_(self.url)
        except Exception:
            self.cancel()
            return
        self.songs.add(filename)
        self.callback.set_result(filename)
        self.notify_status(Downloader.Status.DONE)
        print('File named: '+str(filename))

    def cancel(self):
        '''Cancela una canción, notificando error (visto en clase)'''
        self.notify_status(Downloader.Status.ERROR)
        self.callback.ice_exception(Downloader.SchedulerCancelJob())
