from torrent import *
from tracker import *
from threading import Thread
from peer import *
import os
import random
import time
from file import *

MAX_VALUE = 1000
MIN_VALUE = 0

class Download():
    def __init__( self, torrent_file_name, max_peers, download_path ):
        self.torrent = Torrent( torrent_file_name )
        self.tracker = Tracker( self.torrent )
        self.max_peers = max_peers

        # print("Total Length", self.torrent.total_length )
        self.file_size = self.torrent.total_length
        self.number_of_pieces = self.torrent.number_of_pieces
        self.bitfield = []
        for i in range( self.number_of_pieces):
            self.bitfield.append(0)

        self.piece_not_downloaded = []
        for i in range( self.number_of_pieces ):
            self.piece_not_downloaded.append(i)

        
        # self.download_path = download_path
        # self.file_name = self.torrent.file_names[0]['path']
        # self.file_name = self.download_path + "/" + self.file_name
        # self.file_ptr = os.open( self.file_name , os.O_RDWR | os.O_CREAT )
        # self.write_null()
        self.files = Multi_file( self.torrent.file_names, self.torrent.piece_length ) 

        self.all_peers = []
        self.active_peers = []
        self.number_of_active_peers = 0
    
    def do_handshake_bitfield( self, p, j ):
        if p.handshake() == True:
            if self.number_of_active_peers < self.max_peers :
                self.active_peers.append(p)
                self.number_of_active_peers += 1
                p.initialize_bitfield()
                n = len( p.bitfield_pieces )
                if n % 8 == 0 and n >= self.number_of_pieces:
                    for i in range( self.number_of_pieces ):
                        self.bitfield[i] += p.bitfield_pieces[i]
                else:
                    p.handshake_flag = False

    def connect_peers( self ):
        thread_pool = []
        j = 0
        for p in self.all_peers:
            th = Thread( target =( self.do_handshake_bitfield ) , args=( p, j ) )
            thread_pool.append(th)
            th.start()
        
        for i in thread_pool:
            i.join()

    def make_peer_object( self, peer_list ):
        for ip, port in peer_list:
            p = Peer( ip, port, self.torrent.info_hash, self.torrent.peer_id )
            self.all_peers.append(p)

    def continuously_contact_peers( self ):
        while len( self.piece_not_downloaded ):
            self.connect_peers()
            sleep(15)

    def continuously_contact_trackers( self ):
        while len( self.piece_not_downloaded ):
            peer_list = self.tracker.get_peers_from_trackers( self.torrent )
            self.make_peer_object( peer_list )
            sleep(15)

    def write_null( self ):
        buff = 8192
        data_size = self.file_size
        while data_size > 0:
            if data_size >= buff:
                data_size = data_size -buff
                data = b'\x00' * buff
            else:
                data = b'\x00' * data_size
                data_size = 0
            os.write(  self.file_ptr, data )
    
    def download_strategy( self, peer_req, piece_index, piece_length ):
        is_piece_downloaded, data = peer_req.download_piece( piece_index, piece_length, self.torrent )
        if is_piece_downloaded:
            self.piece_not_downloaded.remove( piece_index)
            self.files.write_in_appropriate_file( piece_index, data )
            # os.lseek( self.file_ptr , piece_index* self.torrent.piece_length , os.SEEK_SET)
            # os.write( self.file_ptr , data )

        if is_piece_downloaded == False :
            self.bitfield[piece_index] = MIN_VALUE
        
        self.active_peers.append( peer_req )
        return

    def download( self ):
        print("Extracting Peers..")
        peer_list = self.tracker.get_peers_from_trackers( self.torrent )
        self.make_peer_object( peer_list )
        print("connecting to peers")
        self.connect_peers()

        print( len(self.active_peers), "peers connected..!!")

        thread_down = Thread( target= self.show_progress, args=( 2,2))
        thread_down.start()

        t1 = Thread( target=self.continuously_contact_peers )
        t1.start()

        t2 = Thread( target=self.continuously_contact_trackers )
        t2.start()


        thread_pool = []
        while len( self.piece_not_downloaded ):
            piece_index, req_peer = self.peer_piece()
            if piece_index != None:
                piece_length = self.torrent.calculate_piece_length( piece_index )

                th = Thread( target = self.download_strategy, args=( req_peer, piece_index, piece_length ))
                thread_pool.append( th )
                th.start()

        for i in thread_pool:
            i.join()

        self.files.close_all_files()
        # os.close( self.file_ptr )

    def peer_piece( self ):
        if not len( self.active_peers ):
            return None, None

        random.shuffle( self.active_peers )
        piece_index = self.bitfield.index( min( self.bitfield ) )
        if piece_index == 0 and self.bitfield[ piece_index ] == MAX_VALUE:
            return None, None

        flag = 0
        for p in self.active_peers:
            if piece_index < len(p.bitfield_pieces) and p.bitfield_pieces[piece_index] :
                flag = 1
                break

        if flag == 1:
            self.active_peers.remove(p)
            self.bitfield[piece_index] = MAX_VALUE
            return piece_index, p

        return None, None
            
    def show_progress( self,i,j ):
        temp = 0
        sleep(i)
        t1 = time.time()

        while len( self.piece_not_downloaded ):
            os.system("clear")
            speed = self.torrent.downloaded_length - temp
            temp = self.torrent.downloaded_length
            perc = ( self.number_of_pieces - len(self.piece_not_downloaded) )/self.number_of_pieces  * 100
            print("[{0}{1}] {2}%".format("#" * round(perc), "." * ( 100-round(perc)) , round(perc, 2)))
            print(
                "Downloading from {} peers out of {} peers at {} KBps.".format(
                    self.number_of_active_peers - len(self.active_peers) ,self.number_of_active_peers , round( speed / 2048, 2)
                )
            )
            sleep(j)
        
        t2 = time.time()
        os.system("clear")
        print("[{0}] 100%".format("#" * 100 ) )
        print("Downloading complete at avg speed of", round( self.torrent.downloaded_length /( 1024*( t2 -t1 )), 2 ),"KBps" )
        return