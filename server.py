#!/usr/bin/python3
# -*- mode:python; coding:utf-8; tab-width:4 -*-
# pylint: disable=import-error
'''Servidor de la aplicación'''

from __future__ import print_function

import sys
import time

from work_queue import WorkQueue
from download_scheduler import DownloadSchedulerI

import Ice
import IceStorm
Ice.loadSlice('downloader.ice')
import Downloader


#key = 'Downloader.IceStorm.Proxy'
KEY = 'Downloader.IceStorm/TopicManager'
SYNC_TOPIC = 'SyncTopic'
PROGRESS_TOPIC = 'ProgressTopic'
DOWNLOADED_FILES = set()
SYNCEVENT = None

class SyncEventI(Downloader.SyncEvent):
    '''Sincronización de los archvos de descarga'''
    def requestSync(self, current=None):
        '''Notifica listando la lista de canciones descargadas'''
        if SYNCEVENT:
            self.notify(list(self.DOWNLOADED_FILES))

    def notify(self, songs, current=None):
        '''Actualiza las canciones descargadas con añadiendo una lista de
        canciones pasada por argumentos'''
        self.DOWNLOADED_FILES = self.DOWNLOADED_FILES.union(set(songs))

class SchedulerFactoryI(Downloader.SchedulerFactory):
    '''Creación de los servidores de descarga'''
    registry = {}
    queue = None
    def __init__(self, queue):
        self.queue = queue

    def make(self, name, current=None):
        '''Crea servidores de decarga dado un nombre y lo mete en una lista de
        servidores de descarga'''
        servant = DownloadSchedulerI(self.queue, DOWNLOADED_FILES)
        if name in self.registry:
            raise Downloader.SchedulerAlreadyExists()
        proxy = current.adapter.add(servant, Ice.stringToIdentity(name))
        print('New scheduler: ' +str(name) +', '+str(proxy))
        self.registry[name] = proxy
        return Downloader.DownloadSchedulerPrx.checkedCast(proxy)

    def kill(self, name, current=None):
        '''Elimina un servidor de descargaa si existe y lo elimina de la lista
        de servidores de descargas'''
        if name not in self.registry:
            raise Downloader.SchedulerNotFound()
        print('Delete scheduler: ' +str(name))
        current.adapter.remove(Ice.stringToIdentity(name))
        del self.registry[name]

    def availableSchedulers(self, current=None):
        '''Retorn la lista de servidores de descarga'''
        return len(self.registry)

class Server(Ice.Application):
    '''Inicialización del server'''
    def get_topic(self, topic_name):
        '''Retorn un topic dado un topic name'''
        proxy = self.communicator().stringToProxy(KEY)
        if proxy is None:
            print("property {0} not set".format(KEY))
            return
        else:
            topic_mgr = IceStorm.TopicManagerPrx.checkedCast(proxy)
            if not topic_mgr:
                print('Error topic')
            try:
                topic = topic_mgr.retrieve(topic_name)
            except IceStorm.NoSuchTopic:
                topic = topic_mgr.create(topic_name)
            finally:
                return topic

    def run(self, args):
        '''Crea los canales de eventos y el proxy que sera mostrado por teminal
        para que el cliente pueda conectarse a el'''
        adapter = self.communicator().createObjectAdapter("FactoryAdapter")
        Downloader.SyncEventPrx.uncheckedCast(self.get_topic(SYNC_TOPIC).getPublisher())
        progress = Downloader.ProgressEventPrx.uncheckedCast(self.get_topic(PROGRESS_TOPIC).getPublisher())
        queue = WorkQueue(progress)
        proxy = adapter.addWithUUID(SchedulerFactoryI(queue))

        print(proxy, flush=True)
        topic_mgr = self.get_topic(SYNC_TOPIC)
        servant = SyncEventI()
        subscriber = adapter.addWithUUID(servant)
        qos = {}
        topic_mgr.subscribeAndGetPublisher(qos, subscriber)

        while self.communicator().isShutdown():
            subscriber.requestSync()
            time.sleep(10)

        adapter.activate()
        queue.start()
        self.shutdownOnInterrupt()
        self.communicator().waitForShutdown()
        queue.destroy()

        return 0

if __name__ == '__main__':
    APP = Server()
    sys.exit(APP.main(sys.argv))
