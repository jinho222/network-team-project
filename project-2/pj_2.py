
import os
from threading import TIMEOUT_MAX
from tkinter.messagebox import NO
# from turtle import st

from config import *
from collections.abc import Callable

import struct
from typing import Tuple, Any

from time import time
from time import sleep

from tkinter import END


UDP_WINDOW_SIZE = 100
UDP_MAX_ACK_NUM = int(2**16)
UDP_TIMEOUT = 5
UDP_WAIT = 0.05

PACKET_TYPE_FILE_START = b'\x00'
PACKET_TYPE_FILE_DATA = b'\x01'
PACKET_TYPE_FILE_END = b'\x02'
PACKET_TYPE_FILE_ACK = b'\x03'

TCP_FILE_TRANSFER_END = PACKET_TYPE_FILE_END + bytes(PACKET_SIZE-1) # TCP에서의 파일 전송 종료를 알리기 위한 패킷


class FileTransfer:
    def __init__(self) -> None:
        self.file_pointer = None
        self.udp_recv_packet = [bytes(PACKET_SIZE) for _ in range(UDP_MAX_ACK_NUM)]
        self.udp_recv_flag = [False for _ in range(UDP_MAX_ACK_NUM)]
        self.udp_send_packet = dict()
        self.udp_ack_windows = [False for _ in range(UDP_MAX_ACK_NUM)]
        self.udp_ack_num = 0
        self.udp_last_ack_num = 0
        self.file_packet_start = 0
        self.file_name = None

    @staticmethod
    def tcp_packet_pack(packet_type: bytes, data: bytes) -> bytes:
        data_len = len(data)
        packet = packet_type + struct.pack(">H", data_len) + data
        packet = packet + bytes(PACKET_SIZE - len(packet)) # packet 크기 맞추기
        return packet
    
    @staticmethod
    def tcp_packet_unpack(packet: bytes) -> Tuple[bytes, bytes]:
        packet_type = packet[:1]
        data_len = struct.unpack(">H", packet[1:3])[0]
        data = packet[3:3+data_len]
        return packet_type, data

    @staticmethod
    def udp_packet_pack(packet_type: bytes, ack_num: Any, data: bytes) -> bytes:
        data_len = len(data)
        if type(ack_num) == int:
            packet = packet_type + struct.pack(">HH", ack_num, data_len) + data
        elif type(ack_num) == bytes:
            packet = packet_type + ack_num + struct.pack(">H", data_len) + data
        packet = packet + bytes(PACKET_SIZE - len(packet)) # packet 크기 맞추기
        return packet
    
    @staticmethod
    def udp_packet_unpack(packet: bytes) -> Tuple[bytes, int, bytes]:
        packet_type = packet[:1]
        ack_num, data_len = struct.unpack(">HH", packet[1:5])
        data = packet[5:5+data_len]
        return packet_type, ack_num, data

    @staticmethod
    def udp_ack_bytes(packet: bytes) -> bytes:
        return packet[1:3]

    def tcp_file_name_packet(self, file_name: str) -> bytes:
        # TCP 통신에서의 file 이름 전송용 패킷 생성 
        # 패킷 구조: \x00 + (이름 data 크기) + (파일 이름 data)
        data = file_name.encode(ENCODING)
        return self.tcp_packet_pack(PACKET_TYPE_FILE_START, data)

    
    def tcp_file_data_packet(self) -> Tuple[bool, bytes]:
        # tcp sener가 가진 self.file_pointer에서
        # 전송을 위한 packet을 생성한다,
        # 결과값: 패킷이 존재 여부, 생성된 패킷
        # 패킷 구조: \x01 + (data 크기) + (file data)
        data = self.file_pointer.read(PACKET_SIZE -1 -2)
        if data:
            return True, self.tcp_packet_pack(PACKET_TYPE_FILE_DATA, data)
        else:
            return False, None
    
    def udp_file_data(self) -> Tuple[bool, bytes]:
        # udp sener가 전송할 file data를 얻는다
        # 결과값: file data
        data = self.file_pointer.read(PACKET_SIZE -1 -2 -2)
        if data:
            return True, data
        else:
            return False, None

    def tcp_file_name_transfer(self, filename: str, tcp_send_func: Callable)-> None:
        # TCP 통신에서 sender에게 파일 전송이 시작을 알리면서 파일 이름을 전송한다.
        packet = self.tcp_file_name_packet(filename)
        tcp_send_func(packet)

    def tcp_file_send(self, filename: str, tcp_send_func: Callable)-> None:
        basename = os.path.basename(filename)
        self.file_pointer = open(filename, "rb")

        # packet의 파일 이름(basename)을 전송한다.
        #
        # todo
        #
        # 이름 전송 종료

        # 파일을 구성하는 data를 전송한다.
        # tcp_file_data_packet이 생성하는 packet을 tcp를 이용해 전부 전송한다.
        #
        # todo
        #
        # 파일 data 전송 종료

        # TCP_FILE_TRANSFER_END을 전송하여 
        # 파일의 전송이 끝냈음을 알린다.
        #
        # todo
        #
        # TCP_FILE_TRANSFER_END을 전송 종료
        

        # 파일 닫기
        self.file_pointer.close()
        self.file_pointer = None
        
            
    def tcp_file_receive(self, packet) -> int:
        packet_type, data = self.tcp_packet_unpack(packet)
        

        if packet_type == PACKET_TYPE_FILE_START:
            basename = data.decode(ENCODING)
            self.file_name = basename
            file_path = './downloads/(tcp) '+basename
            # 파일의 이름을 받아 file_path 위치에 self.file_pointer를 생성한다.
            #
            # todo
            #
            return 0

        elif packet_type == PACKET_TYPE_FILE_DATA:
            # self.file_pointer에 전송 받은 data를 저장한다.
            # todo
            # 
            return 1
            
        elif packet_type == PACKET_TYPE_FILE_END:
            # 파일 전송이 끝난 것을 확인하고 file_pointer를 종료한다.
            # 
            # todo
            #
            return 2

    def udp_file_name_transfer(self, file_name: str, udp_send_func: Callable)-> None:
        data = file_name.encode(ENCODING)
        self.udp_send_with_record(PACKET_TYPE_FILE_START, data, udp_send_func)

    def udp_send_with_record(self, packet_type: bytes, data: bytes, udp_send_func: Callable) -> None:
        packet = self.udp_packet_pack(packet_type, self.udp_last_ack_num, data)
        udp_send_func(packet)
        # GBN, SR을 통한 재전송을 위해 packet과 전송 시간을 self.udp_send_packet에 저장한다.
        # 또한 self.udp_lask_ack_num을 update하여 새로 전송할 packet의 ack_num을 update한다.
        # 
        # todo
        #

    def udp_file_send(self, filename: str, udp_send_func: Callable) -> None:
        basename = os.path.basename(filename)
        self.file_pointer = open(filename, "rb")
        # udp를 통해 파일의 basename을 전송하고 ack를 기다린다.
        # hint : self.udp_file_name_transfer 함수를 활용할 것
        # 
        # todo
        #
        
        data_ready, data = self.udp_file_data()
        while data_ready:
            if len(self.udp_send_packet) < UDP_WINDOW_SIZE: #window의 크기보다 전송한 패킷의 양의 적은 경우
                # 
                # todo
                #

                data_ready, data = self.udp_file_data() # 다음 전송할 data를 준비한다.

            else:
                # PIPELINE을 위한 window를 전체를 사용하여 ack를 기다리며 timeout에 대처한다.
                # Timeout이 아닌 경우에는 Sleep(UDP_WAIT)를 사용한다.
                #
                # todo
                #
                pass
        # 모든 파일 data의 ack를 기다리고 timeout에 대처한다.
        #
        # todo
        #
        
        # 파일 전송이 완료되었음을 알리고 ack에 대비한다.
        # 
        # todo
        #
        
        # 파일 포인터를 제거한다.
        self.file_pointer.close()
        self.file_pointer = None
            
    def udp_file_receive(self, packet: bytes, udp_send_func: Callable) -> int:
        ack_bytes = self.udp_ack_bytes(packet)
        packet_type, ack_num, data = self.udp_packet_unpack(packet)

        if packet_type != PACKET_TYPE_FILE_ACK:
            # 받은 packet에 대한 ack를 전송한다.
            #
            # todo
            #
            pass

        if packet_type == PACKET_TYPE_FILE_START:  # file transfer start
            if self.file_pointer is not None:
               self.file_pointer.close()

            basename = data.decode(ENCODING)            
            self.file_name = basename
            file_path = './downloads/(udp) '+basename
            # 파일의 이름을 받아 file_path 위치에 self.file_pointer를 생성하고.
            # 그다음 받을 파일의 data의 시작 packet의 ack_num를 self.file_packet_start에 저장하여
            # 연속된 packet을 받을 수 있게 준비한다.
            #
            # todo
            #
            return 0

        elif packet_type == PACKET_TYPE_FILE_DATA:  # file transfer
            if not self.udp_recv_flag[ack_num]:
                # 처음 받은 packet인지 확인하고
                # 처음 받은 packet이라면 self.udp_recv_packet[ack_num]에 저장하고
                # self.udp_recv_flag[ack_num]에서 확인할 수 있게 표시한다.
                #
                # todo
                #
                pass
            
            # self.udp_recv_packet에 self.file_packet_start에서 부터 연속된
            # 패킷이 저장되어 있다면 이를 self.file_pointer를 이용해 파일로 저장하고 
            # self.udp_recv_flag를 update한다.
            # 또한 self.file_packet_start 역시 update한다.
            # 
            # todo
            #
            return 1

            
        elif packet_type == PACKET_TYPE_FILE_END:  # file transfer end
            # 파일 전송이 끝난 것을 확인하고 파일을 종료한다.
            if self.file_pointer is not None:
                self.file_pointer.close()
                self.file_pointer = None
            return 2
        
        elif packet_type == PACKET_TYPE_FILE_ACK:  # ack
            # GBN, SR을 위해 self.udp_ack_windows를 update한다.
            # hint: self.udp_ack_num으로 부터 연속되게 ack를 받은 경우
            # window를 옮겨준다 (self.udp_send_packet에 저장된 packet도 처리해줄 것)
            # 
            # todo
            #
            return 1
        return 1

    def udp_time_out(self) -> bool:
        if time() - self.udp_send_packet[self.udp_ack_num][0] > UDP_TIMEOUT: # timeout
            return True
        else:
            return False

    def udp_pipeline(self, udp_send_func: Callable) -> None:
        # GBN, SR 중 하나의 알고리즘을 선택하여 ACK를 관리한다.
        # def udp_gbn () or def udp_sr()로 구현
         # hint: self.udp_send_packet[ack_num]에 저장시
        # (send time, packet)형태로 저장할 것
        #
        #
        # udp_file_send()에서 사용
        pass

    def udp_ack_send(self, ack_bytes: bytes, udp_send_func: Callable):
        packet = PACKET_TYPE_FILE_ACK + ack_bytes
        packet = self.udp_packet_pack(PACKET_TYPE_FILE_ACK, ack_bytes, b'')
        udp_send_func(packet)
