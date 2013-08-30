# -*- coding: utf-8 -*-

import os, json
from hashlib import sha1
import tornado.web
from torrent import TorrentReceiver, TorrentGenerator, GridTorrentGenerator
from crypto import Receiver

"""
This is the modcommon.fileserver.FileReceiver copied from mod-python.
We do this to avoid the risk of breaking this library during an upgrade of mod-python
"""

class FileReceiver(tornado.web.RequestHandler):
    @property
    def download_tmp_dir(self):
        raise NotImplemented
    @property
    def remote_public_key(self):
        raise NotImplemented
    @property
    def destination_dir(self):
        raise NotImplemented

    @classmethod
    def urls(cls, path):
        return [
            (r"/%s/$" % path, cls),
            (r"/%s/([a-f0-9]{32})/(\d+)$" % path, cls),
            #(r"/%s/([a-f0-9]{40})/(finish)$" % path, cls),
            ]

    @tornado.web.asynchronous
    def post(self, sessionid=None, chunk_number=None):
        if self.request.connection.stream.closed():
            return self.finish()
        self.set_header('Access-Control-Allow-Origin', self.request.headers['Origin'])
        # self.result can be set by subclass in process_file,
        # so that answer will be returned to browser
        self.result = None
        if sessionid is None:
            self.generate_session()
        else:
            self.receive_chunk(sessionid, int(chunk_number))

    def generate_session(self):
        """
        This Handler receives a torrent file and returns a session id to browser, so that
        chunks of this file may be uploaded through ChunkUploader using this session id
        
        Subclass must implement download_tmp_dir, remote_public_key properties and destination_dir
        """
        torrent_data = self.request.body
        receiver = TorrentReceiver(download_tmp_dir=self.download_tmp_dir, 
                                   remote_public_key=self.remote_public_key,
                                   destination_dir=self.destination_dir)

        try:
            receiver.load(torrent_data)
        except Receiver.UnauthorizedMessage:
            self.write(json.dumps({ 'ok': False,
                                    'reason': "This file's source cannot be recognized. Downloading it is not safe",
                                    }))
            self.finish()
            return
                        
        info = {
            'ok': True,
            # using int instead of boolean saves bandwidth
            'status': [ int(i) for i in receiver.status ], 
            'id': receiver.torrent_id,
            }

        def finish():
            self.set_header('Content-type', 'application/json')
            info['result'] = self.result
            self.write(json.dumps(info))
            self.finish()
            
        if receiver.complete:
            try:
                receiver.torrent.pop('data')
            except KeyError:
                pass
            receiver.finish()
            self.process_file(receiver.torrent, callback=finish)
        else:
            finish()
        
    def receive_chunk(self, torrent_id, chunk_number):
        """
        This Handler receives chunks of a file being uploaded, previously registered 
        through FileUploader.
        
        Subclass must implement download_tmp_dir and destination_dir property
        """
        receiver = TorrentReceiver(torrent_id,
                                   download_tmp_dir=self.download_tmp_dir, 
                                   destination_dir=self.destination_dir)
        receiver.receive(chunk_number, self.request.body)
        response = { 'torrent_id': torrent_id,
                     'chunk_number': chunk_number,
                     'percent': receiver.percent,
                     'complete': False,
                     'ok': True,
                     }
        def finish():
            self.set_header('Content-type', 'application/json')
            response['result'] = self.result
            self.write(json.dumps(response))
            self.finish()
            
        if receiver.complete:
            response['complete'] = True
            receiver.finish()
            self.process_file(receiver.torrent, callback=finish)
        else:
            finish()
        

    def process_file(self, file_data, callback):
        """
        To be overriden
        """
