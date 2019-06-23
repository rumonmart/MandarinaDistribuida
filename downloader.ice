// -*- mode:c++ -*-

module Downloader {

  sequence<string> SongList;
  enum Status {PENDING, INPROGRESS, DONE, ERROR};

  struct ClipData {
    string URL;
    Status status;
  };

  exception SchedulerAlreadyExists {};
  exception SchedulerNotFound {};
  exception SchedulerCancelJob {};

//lista
  interface Transfer {
    string recv(int size);
    void end();
  };

//lista
  interface DownloadScheduler {
    SongList getSongList();
    ["amd", "ami"] void addDownloadTask(string url) throws SchedulerCancelJob;
    ["ami"] Transfer* get(string song);
    void cancelTask(string url);
  };

//lista
  interface SchedulerFactory {
    DownloadScheduler* make(string name) throws SchedulerAlreadyExists;
    void kill(string name) throws SchedulerNotFound;
    int availableSchedulers();
  };

  interface ProgressEvent {
    void notify(ClipData clipData);
  };

//lista
  interface SyncEvent {
    void requestSync();
    void notify(SongList songs);
  };
};
