import os
import math

BUFFER = 65536
BUFFER_DATA = b'\x00' * BUFFER

class FILE():
    def __init__( self, file_info, start_index, end_index, start_offset, end_offset ):
        self.file_name    = file_info['path']
        self.file_length  = file_info['length']
        self.file_ptr     = os.open( self.file_name , os.O_RDWR | os.O_CREAT )
        self.start_index  = start_index
        self.end_index    = end_index
        self.start_offset = start_offset
        self.end_offset   = end_offset
        self.write_null()
        print("*------------------------------------------------------------------*")
        print("file name", self.file_name)
        print("file size", self.file_length)
        print("start index", self.start_index)
        print("end index", self.end_index)
        print("start offset", self.start_offset)
        print("end offset", self.end_offset)
        print("*------------------------------------------------------------------*")

    def write_null( self ):
        data_size = self.file_length
        while data_size > 0:
            if data_size >= BUFFER:
                data_size = data_size - BUFFER
                os.write(  self.file_ptr, BUFFER_DATA )
            else:
                data = b'\x00' * data_size
                data_size = 0
                os.write(  self.file_ptr, data )
        return

class Multi_file():
    def __init__( self, files_info, piece_length ):
        self.file_objects = []
        self.piece_length = piece_length
        
        n = len( files_info )
        start_index  = 0
        start_offset = 0
        total_length = 0

        for i in range(n):
            file_info = files_info[i]
            total_length += file_info['length']
            end_index     = math.ceil( total_length / piece_length ) - 1
            end_offset    = total_length - self.piece_length * end_index 
            
            f_object = FILE( file_info, start_index, end_index, start_offset, end_offset )
            self.file_objects.append( f_object )

            if( end_offset == self.piece_length ):
                start_index  = end_index + 1
                start_offset = 0
            else:
                start_index = end_index
                start_offset = end_offset

    def write_in_appropriate_file( self, piece_index, data ):
        for f_object in self.file_objects:
            if piece_index >= f_object.start_index and piece_index <= f_object.end_index:
                if piece_index == f_object.start_index:
                    offset = 0
                else:
                    if( f_object.start_offset == 0 ):
                        offset = ( piece_index - f_object.start_index )*self.piece_length
                    else:
                        offset = self.piece_length - f_object.start_offset + ( piece_index - f_object.start_index-1 )*self.piece_length

                os.lseek( f_object.file_ptr , offset , os.SEEK_SET)

                if( piece_index == f_object.start_index ):
                    data_to_be_write = data[f_object.start_offset : ]
                elif piece_index == f_object.end_index :
                    data_to_be_write = data[ : f_object.end_offset ]
                else:
                    data_to_be_write = data

                os.write( f_object.file_ptr , data_to_be_write )
    
    def close_all_files( self ):
        for f_object in self.file_objects:
            os.close( f_object.file_ptr )