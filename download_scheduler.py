#!/usr/bin/python3
# -*- mode:python; coding:utf-8; tab-width:4 -*-
# pylint: disable=import-error
'''Servidor de descarga'''

from __future__ import print_function

import binascii

import Ice
Ice.loadSlice('downloader.ice')
import Downloader

class TransferI(Downloader.Transfer):
    '''Transfer file'''
    def __init__(self, local_filename):
        self.file_contents = open(local_filename, 'rb')

    def recv(self, size, current=None):
        '''Send data block to client'''
        return str(
            binascii.b2a_base64(self.file_contents.read(size), newline=False)
        )

    def end(self, current=None):
        '''Close transfer and free objects'''
        self.file_contents.close()
        current.adapter.remove(current.id)


class DownloadSchedulerI(Downloader.DownloadScheduler):
    '''Funciones Scheduler'''
    task = None
    downloaded_files = None

    def __init__(self, queue, downloaded_files):
        '''Inicializa el servidor de descarga dada una tarea de trabajos y una
        lista de canciones descargadas'''
        self.task = queue
        self.downloaded_files = downloaded_files

    def addDownloadTask(self, url, current=None):
        '''Para una url dada lo mete en la cola de tareas y la manda ejecutar
        (callback visto en clase)'''
        callback = Ice.Future()
        self.task.add(callback, url, self.downloaded_files)
        return callback

    def getSongList(self, current=None):
        '''Retorna la lista de canciones descargadas'''
        return list(self.downloaded_files)

    def get(self, song, current=None):
        '''Dada una canción la obtiene y almacena en local (visto en clase)'''
        proxy = current.adapter.addWithUUID(TransferI(song))
        return Downloader.TransferPrx.checkedCast(proxy)

    def cancelTask(self, url, current=None):
        '''Elimina una canción de la cola de trabajos dada una url'''
        self.task.destroy_job(url)
