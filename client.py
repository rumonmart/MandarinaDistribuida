#!/usr/bin/python3
# -*- mode:python; coding:utf-8; tab-width:4 -*-
# pylint: disable=import-error
'''Cliente de la aplicación'''

from __future__ import print_function
import os
import cmd
import sys
import uuid
import random
import binascii

import Ice
Ice.loadSlice('downloader.ice')
import Downloader
import IceStorm

BLOCK_SIZE = 10240


KEY = 'Downloader.IceStorm/TopicManager'
#key = 'Downloader.IceStorm.Proxy'
TOPIC_NAME = 'ProgressTopic'
SONG_STATUS = dict()

class Shell(cmd.Cmd):
    '''Menú con los comandos disponibles'''
    prompt = 'Client> '
    client = None
    '''Añade los métodos get, set y delete al objeto creado (visto en clase)'''
    @property
    def online(self):
        '''comprueba que el cliente esta conectado (visto en clase)'''
        if self.client is None:
            return False
        return self.client.factory is not None

    def text_shell(self):
        '''Si el cliente esta conectado muestra "Client (connected)>",
        si no es así, muestra "Client" en el Shell'''
        if self.online:
            self.prompt = 'Client (connected)> '
        else:
            self.prompt = 'Client> '

    def precmd(self, line):
        '''(visto en clase)'''
        self.text_shell()
        return line

    def postcmd(self, stop, line):
        '''(visto en clase)'''
        self.text_shell()
        return stop

    def emptyline(self):
        '''(visto en clase)'''
        pass

    def default(self, line):
        '''Para cada linea entrante, comprubea si inicia con "#" o "//" si así
        continua, en caso negativo retorna un error (visto en clase)'''
        line = line.strip()
        if line.startswith('#') or line.startswith('//'):
            return
        print('Unknown command: %s' % line.split()[0])

    def do_connect(self, line):
        '''Comprueba que la linea de entrada no esté vacia y el cliente esté
        conectado, si ya está retorna un error "Ya conectado", y si no está, se
        conecta usando los parámetos de entrada, si no se puede conectar por
        nombre incorrecto de proxy muestra "proxy no valido"'''
        if line == '':
            print("No empty line allowed")
            return
        else:
            if self.online:
                print('Already connected')
                return
            else:
                try:
                    self.client.connect(line)
                except Ice.NotRegisteredException as error:
                    print("No valid proxy " +str(error))
                    return
                except Ice.ObjectNotExistException as error:
                    print("Proxy does not exist " +str(error))
                    return

    def do_disconnect(self, line):
        '''Comprueba si el cliente esta conectado, si no está retorna un error
        "No conectado", y si no está, se desconecta'''
        if not self.online:
            print('Youre not connected')
            return
        else:
            self.client.disconnect()

    def do_exit(self, line):
        '''Si el cliente esta conectado, se desconecta y en el caso contrario
        llama a EOF'''
        if self.online:
            try:
                self.do_disconnect(line)
            except Ice.ObjectNotExistException as error:
                print("No valid proxy " +str(error))
        return True

    def do_create_scheduler(self, line):
        '''Comprueba la conexión del cliente, en caso afirmativo crea un un nuevo
        servidor de descarga (Método visto en clase)'''
        if not self.online:
            print('Youre not connected to a factory')
            return
        else:
            if line == '':
                name = str(uuid.uuid4())
            else:
                name = line
            try:
                self.client.create_scheduler(name)
            except Exception as error:
                print('ERROR: ' +str(error))

    def do_delete_scheduler(self, line):
        '''Comprueba la conexión del cliente y que le entre por parámetros una línea
        de texto, en caso afirmativo elimina el servidor de desacarga llamado como
        la línea de texto de entrada'''
        if not self.online:
            print('Youre not connected to a factory')
            return
        else:
            if line == '':
                print("No empty line allowed")
                return
            else:
                try:
                    self.client.delete_scheduler(line)
                except Exception as error:
                    print('Error: '+str(error))

    def do_list_creatded_shedulers(self, line):
        '''Si existen servidores de descarga creados, este el cliente conectado
        o no, recorre la lista de servidores y los muestra'''
        if not self.online:
            print('Youre not connected to a factory')
            return
        else:
            self.client.list_scheduler()

    def do_download_song(self, line):
        '''Comprueba si el cliente está conectado y añade una una canción de
        descarga, con una url pasada por parámetos'''
        if not self.online:
            print('Youre not connected to a factory')
            return
        else:
            if line == '':
                print("No empty line allowed")
                return
            else:
                self.client.download_song(line)

    def do_cancell_download_song(self, line):
        '''Comprueba si el cliente está conecyado y cancela la descarga de una
        canción pasada la url por parámetos'''
        if not self.online:
            print('Youre not connected to a factory')
            return
        else:
            if line == '':
                print("No empty line allowed")
                return
            else:
                self.client.cancell_song(line)

    def do_list_download_songs(self, line):
        '''Obtiene una lista con las canciones descargadas, si esa lista está
        vacía muestra que no hay canciones y en caso contrario muestra las
        canciones una a una'''
        if not self.online:
            print('Youre not connected to a factory')
            return
        else:
            self.client.list_songs()

    def do_get_download_song(self, line):
        '''Obtine y almacena en local una cación con una url dada por parámetos'''
        if not self.online:
            print('Youre not connected to a factory')
            return
        else:
            if line == '':
                print("No empty line allowed")
                return
            else:
                try:
                    self.client.get(line)
                except Ice.UnknownException as error:
                    print('Error: ' +str(error))

    def do_status_song(self, line):
        '''Recorre el diccionario y muestra la "key" url de la canción y el
        "value" estado de la canción, no es necesario que el cliente esté conectado'''
        if not self.online:
            print('Youre not connected to a factory')
            return
        else:
            self.client.list_status_songs()

class ProgressEventI(Downloader.ProgressEvent):
    def notify(self, clipData, current=None):
        '''Cuando el publicador cambia de estado una canción este método es llamado
        con el evento y modifica la biblioteca de estado de las canciones con la url,
        y el nuevo estado de la canción'''
        SONG_STATUS[clipData.URL] = clipData.status

class Client(Ice.Application):
    '''Da funcionalidad a los métodos del shell'''
    factory = None
    schedulers = {}
    '''Añade los métodos get, set y delete al objeto creado (visto en clase)'''
    @property
    def scheduler(self):
        '''Comprueba la conexión del cliente y selecciona aleatoriamente un
        servidor de descarga, si no hay ninguno, se crea uno (visto en clase)'''
        if not self.factory:
            print ('Not connected to a proxy')
            return
        else:
            if not self.schedulers:
                self.create_scheduler(str(uuid.uuid4()))
            return random.choice(list(self.schedulers.values()))

    def connect(self, proxy):
        '''Conexión del cliente al proxy del servidor, tambien se crea el
        subscriptor del canal de eventos SYNC_TOPIC'''
        proxy = self.communicator().stringToProxy(proxy)
        if not proxy:
            print('ERROR: invalid proxy')
            return
        else:
            self.factory = Downloader.SchedulerFactoryPrx.checkedCast(proxy)
            self.connect_topic()
            if not self.factory:
                print('ERROR: invalid factory')
                return

    def disconnect(self):
        '''Desconexión del cliente del servidor, comprobando si el cliente está
        conectado a la factoría, se eliminan los servidores de descarga creados'''
        if self.factory is None:
            return
        else:
            for i in self.schedulers.keys():
                self.factory.kill(i)
            self.factory = None
            self.schedulers = {}

    def create_scheduler(self, name):
        '''Comprueba si el cliente esta conectado con la factoría, si está,
        añade el nombre del servidor de desacarga que le entra por parámetos a
        un Array, y el servidor de descarga creado'''
        if self.factory is None:
            print('You are not connected')
            return
        else:
            try:
                self.schedulers[name] = self.factory.make(name)
                print(' ***New Scheduler created***')
                print('     Scheduler name: ' +str(name))
                print('     Scheduler proxy: '+str(self.schedulers[name]))
            except Downloader.SchedulerAlreadyExists:
                print('Scheduler already created')
                return

    def delete_scheduler(self, name):
        '''Comprueba si el cliente esta conectado con la factoría, si está,
        elimina el servidor de descarga de la lista de servidores de descarga y
        destruye el servidor de descarga con el nombre pasado por parámetros'''
        print('     Trying to delete: '+str(name))
        if self.factory is None:
            print('You are not connected')
            return
        else:
            try:
                self.factory.kill(name)
                del self.schedulers[name]
                print('     Scheduler delete')
            except Downloader.SchedulerNotFound:
                print('Sheduler: ' +str(name))
                return

    def list_scheduler(self):
        '''lista los servidores de descarga simpre que tenga alguno'''
        if not self.schedulers:
            print('No schedulers created')
        else:
            print('***Schedulers created***')
            for i in self.schedulers:
                print('     Scheduler name: ' +str(i))

    def download_song(self, url):
        '''Envia al servidor de descarga una canción con una url pasada
        por parámetros de forma asincrona'''
        print('***Downloading song***')
        self.scheduler.begin_addDownloadTask(url)

    def cancell_song(self, url):
        '''Cancela una canción de la cola de descargas llamda con con una url
        pasada por parámetos'''
        print('***Cancell song: '+str(url)+"***")
        self.scheduler.cancelTask(url)

    def list_songs(self):
        '''Lista las canciones descargadas siempre que exista alguna'''
        song = self.scheduler.getSongList()
        if not song:
            print('No songs available')
            return
        else:
            for i in song:
                print('Song: ' +str(i))

    def list_status_songs(self):
        '''recorre el diccionario mostrando sus valores clave, valor'''
        for j, i in SONG_STATUS.items():
            print("Song: {0} -> {1}".format(j, i))

    def get(self, song, destination='./'):
        '''Método asíncorono para obtener una canción dada una url y guardarla
        en local (visto en clase)'''
        async_result = self.scheduler.begin_get(song)
        transfer = self.scheduler.end_get(async_result)
        with open(os.path.join(destination, song), 'wb') as file_contents:
            remote_EOF = False
            while not remote_EOF:
                data = transfer.recv(BLOCK_SIZE)
                # Remove additional byte added in str() cast at server
                if len(data) > 1:
                    data = data[1:]
                data = binascii.a2b_base64(data)
                remote_EOF = len(data) < BLOCK_SIZE
                if data:
                    file_contents.write(data)
            transfer.end()

    def connect_topic(self):
        '''Realiza la subscripción al canal de eventos PROGRESS_TOPIC'''
        proxy = self.communicator().stringToProxy(KEY)
        if proxy is None:
            print("property {0} not set".format(KEY))
            return
        else:
            print("using icestorm in: '%s'" % KEY)
            topic_mgr = IceStorm.TopicManagerPrx.checkedCast(proxy)
            if not topic_mgr:
                print('Error topic')
            try:
                topic = topic_mgr.retrieve(TOPIC_NAME)
            except IceStorm.NoSuchTopic:
                topic = topic_mgr.create(TOPIC_NAME)
            broker = self.communicator()
            servant = ProgressEventI()
            adapter = broker.createObjectAdapter("FactoryAdapter")
            subscriber = adapter.addWithUUID(servant)
            qos = {}
            topic.subscribeAndGetPublisher(qos, subscriber)
            adapter.activate()

    def run(self, argv):
        '''Incia el cliente llamado al shell y dejandolo en bucle'''
        shell = Shell()
        shell.client = self
        shell.cmdloop()
        return 0

sys.exit(Client().main(sys.argv))
