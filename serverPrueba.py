#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import time
import uuid
import binascii

import Ice
import IceStorm
Ice.loadSlice('downloader.ice')
import Downloader


BLOCK_SIZE = 10240
ICESTORM_MANAGER = 'Downloader.IceStorm/TopicManager'
STATUS_TOPIC = 'ProgressTopic'

SONGS = {
    "https://www.youtube.com/watch?v=gV6RrbXqRmM": "./Los Chikos del Maíz - Los hijos de Iván Drago (con Pablo Hásel).mp3",
    "https://www.youtube.com/watch?v=TmrosfxGifQ": "./Pop Team Epic – Opening Theme.mp3",
    "https://www.youtube.com/watch?v=_rp97zjvIBo": "./LOL- LOS GANGLIOS.mp3",
    "https://www.youtube.com/watch?v=88QCGGzcpM8": "./Los Gandules - Prendas trencas topic (Así es mi abrigo).mp3"
}

SONGS_LIST = list(SONGS.keys())
MAX_TIMEOUT = 120.0


def download(remote_file, filename):
    with open(filename, 'wb') as fd:
        remote_EOF = False
        while not remote_EOF:
            data = remote_file.recv(BLOCK_SIZE)
            # Remove additional byte added in str()
            if len(data) > 1:
                data = data[1:]
            data = binascii.a2b_base64(data)
            remote_EOF = len(data) < BLOCK_SIZE
            if data:
                fd.write(data)
    remote_file.end()


class ProgressUpdater(Downloader.ProgressEvent):
    def __init__(self):
        self.status = {}

    def notify(self, clipData, current=None):
        if clipData.URL not in self.status:
            self.status[clipData.URL] = []
        self.status[clipData.URL].append(clipData.status)


class FactoryTest(Ice.Application):
    def get_topic(self, topic_name):
        topic_mgr_proxy = self.communicator().stringToProxy(ICESTORM_MANAGER)
        if topic_mgr_proxy is None:
            raise Exception('Cannot found {0}'.format(ICESTORM_MANAGER))
        topic_mgr = IceStorm.TopicManagerPrx.checkedCast(topic_mgr_proxy)
        if not topic_mgr:
            raise Exception('Cannot cast IceStorm proxy')
        try:
            topic = topic_mgr.retrieve(topic_name)
        except IceStorm.NoSuchTopic:
            topic = topic_mgr.create(topic_name)
        finally:
            return topic

    def run(self, argv):
        points = 0.0

        print('Initializing...')
        # Get a DownloaderFactory object
        proxy = self.communicator().stringToProxy(argv[1])
        factory = Downloader.SchedulerFactoryPrx.checkedCast(proxy)
        if not factory:
            print('Cannot start with tests')
            raise RuntimeError('Invalid factory proxy')
        # Subscribe a ProgressEvent() consumer
        adapter = self.communicator().createObjectAdapter("ClientAdapter")
        progress_topic = self.get_topic(STATUS_TOPIC)
        progress = ProgressUpdater()
        subscriber = adapter.addWithUUID(progress)
        progress_topic.subscribeAndGetPublisher({}, subscriber)
        adapter.activate()

        # Test 00A: get available schedulers
        print('Testing "availableSchedulers()" (initial)')
        initial_schedulers = None
        try:
            initial_schedulers = factory.availableSchedulers()
            print(' -> Initial schedulers: %s' % initial_schedulers)
            points += 0.75
        except Exception as error:
            print('Failed: %s' % error)

        # Test 01A: make a new scheduler
        print('Testing "make()" (initial)')
        try:
            sched1_name = str(uuid.uuid4())
            scheduler1 = factory.make(sched1_name)
            points += 1.0
        except Exception as error:
            print('Failed: %s' % error)
            sys.exit(1)

        # Test 00B: get available schedulers
        print('Testing "availableSchedulers()" (after factory calls)')
        if initial_schedulers is not None:
            try:
                current_schedulers = factory.availableSchedulers()
                if current_schedulers != (initial_schedulers + 1):
                    print('Failed: wrong value in availableSchedulers()')
                else:
                    points += 0.5
            except Exception as error:
                print('Failed: %s' % error)

        # Test 01B: create already-exists DownloaderScheduler()
        print('Testing "make()" (duplicated schedulers)')
        try:
            dummy = factory.make(sched1_name)
            good_exception = False
        except Downloader.SchedulerAlreadyExists:
            good_exception = True
            points += 0.75
        except Exception as error:
            good_exception = False
            print(
                'Failed: expected "SchedulerAlreadyExists" but get: %s' % error
            )
        if not good_exception:
            print('Failed: make a duplicated scheduler reports NO ERROR')

        # Test 02A: obtain initial available songs
        print('Testing "getSongList()" (initial)')
        try:
            initial_songs = scheduler1.getSongList()
            points += 0.5
        except Exception as error:
            print('Failed: cannot get initial songs list (%s)' % error)
            initial_songs = []
        if isinstance(initial_songs, list):
            initial_songs = set(initial_songs)
            points += 0.1
        else:
            print('Failed: songs list is "%s" instead of list' % type(initial_songs))
            initial_songs = set()

        # Test 03A: add a download
        print('Testing "addDownloadTask()" (initial)')
        try:
            now = time.time()
            scheduler1.addDownloadTask(SONGS_LIST[0])
            process_time = time.time() - now
            points += 0.75
        except Exception as error:
            print('Failed: cannot add task (%s)' % error)
            process_time = -1.0

        if process_time > 2.0:
            print('Warning: process time too high: %s ' % process_time)

        time.sleep(1.0)
        current_states = progress.status.get(SONGS_LIST[0], None)
        if current_states is None:
            print('Failed: no status received for task')
        else:
            points += 0.25
            for expected_status in [
                    Downloader.Status.PENDING, Downloader.Status.INPROGRESS
            ]:
                if expected_status not in current_states:
                    print('Failed: expected status "%s" not received' % expected_status)
                else:
                    points += 0.25
        print(' -> waiting DONE status')
        now = time.time()
        while Downloader.Status.DONE not in current_states:
            current_states = progress.status.get(SONGS_LIST[0], None)
            if time.time() - now > MAX_TIMEOUT:
                print('Failed: DONE event not received after timeout')
                break
            time.sleep(1.0)
        if Downloader.Status.DONE in current_states:
            points += 1.0

        # Test 02B: obtain available songs with downloads
        print('Testing "getSongList()" (after download)')
        current_songs = set(scheduler1.getSongList())
        expected_filename = (current_songs - initial_songs)

        if len(expected_filename) != 1:
            print('Warning: expected one filename but got: %s' % expected_filename)
            expected_filename = None
        else:
            expected_filename = expected_filename.pop()
            points += 0.5

        # Test 04A: get file
        print('Testing "get()"')
        try:
            remote_file = scheduler1.get(expected_filename)
        except Exception as error:
            print('Error: cannot get file %s: %s' % (expected_filename, error))
            remote_file = None

        if remote_file is not None:
            try:
                print(' -> downloading file %s' % expected_filename)
                download(remote_file, expected_filename)
                points += 1.5
            except Exception as error:
                print('Error: cannot transfer file: %s' % error)

        # Test 03B: add downloads quickly
        print('Sending some addDownloadTask() requests')
        try:
            now = time.time()
            scheduler1.addDownloadTask(SONGS_LIST[1])
            process_time = time.time() - now
            scheduler1.addDownloadTask(SONGS_LIST[2])
            process_time2 = time.time() - now
            if (process_time > 2.0) or (process_time2 > 2.0):
                print('Warning: process time too high (%s, %s)' % (
                    process_time,
                    process_time2
                ))
            points += 0.5
        except Exception as error:
            print('Error: error adding two tasks quickly: %s' % error)

        # Test 01C: create another DownloadScheduler
        print('Create another DownloadScheduler()')
        try:
            sched2_name = str(uuid.uuid4())
            scheduler2 = factory.make(sched2_name)
            points += 0.5
        except Exception as error:
            print('Failed: %s' % error)
            scheduler2 = None

        # Test 03C: add downloads in alternate scheduler
        print('Create new task in the alternate DownloadScheduler()')
        try:
            scheduler2.addDownloadTask(SONGS_LIST[3])
            points += 0.5
        except Exception as error:
            print('Failed: %s' % error)

        current_states = progress.status.get(SONGS_LIST[3], None)
        if current_states is None:
            print('Failed: no status received for task')
        else:
            for expected_status in [
                    Downloader.Status.PENDING, Downloader.Status.INPROGRESS
            ]:
                if expected_status not in current_states:
                    print('Failed: expected status "%s" not received' % expected_status)
        print(' -> waiting DONE status')
        now = time.time()
        while Downloader.Status.DONE not in current_states:
            current_states = progress.status.get(SONGS_LIST[3], None)
            if time.time() - now > MAX_TIMEOUT:
                print('Failed: DONE event not received after timeout')
                break
            time.sleep(1.0)

        # Test 5: test synchronization
        print('Waiting for synchronization cycle...')
        time.sleep(6.0)
        print('Get song list for both schedulers')
        try:
            songs1 = set(scheduler1.getSongList())
            songs2 = set(scheduler2.getSongList())
        except Exception as error:
            print('Failed: cannot get initial songs lists (%s)' % error)

        if songs1 != songs2:
            print('Failed: schedulers reports different songs lists')
            print(' -> Scheduler1: %s' % ', '.join(list(songs1)))
            print(' -> Scheduler2: %s' % ', '.join(list(songs2)))
        else:
            points += 1.5
        # Test 6: kill schedulers
        print('Kill schedulers...')
        try:
            factory.kill(sched2_name)
            points += 0.5
        except Exception as error:
            print('Error: cannot remove alternate scheduler: %s' % error)
        try:
            factory.kill(sched1_name)
            points += 0.5
        except Exception as error:
            print('Error: cannot remove main scheduler: %s' % error)

        print('Check remainder schedulers...')
        try:
            current_schedulers = factory.availableSchedulers()
            print(' -> Current schedulers: %s' % current_schedulers)
        except Exception as error:
            print('Failed: %s' % error)
        if current_schedulers != initial_schedulers:
            print('Error: final schedulers should be %s not %s' % (
                initial_schedulers, current_schedulers
            ))
        else:
            points += 0.50

        print('\n-> Score points: %s' % (points / 2.0))
        return 0

sys.exit(FactoryTest().main(sys.argv))
