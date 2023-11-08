import struct
from threading import Thread
from time import sleep
from pj_1 import NetworkSocket
from pj_2 import FileTransfer
from config import *
from tkinter import END
import time



class OperationManager:
    def __init__(self) -> None:
        self.network_socket = NetworkSocket()
        self.file_transper = FileTransfer()
        self.server_open_thr = None
        self.tcp_box_thread = None
        self.udp_box_thread = None
        
        self.tcp_thr_flag = True
        self.udp_thr_flag = True

        self.tcp_box = None
        self.udp_box = None
    
    def open_server(self, host: str, tcp_port: int, udp_port: int) -> Thread:
        if host == DEFAULT_IP:
            host = DEFAULT_SERVER_BIND
        
        thr = Thread(target=self.network_socket.server_open_func, args=(host, tcp_port, udp_port))
        thr.daemon = True
        thr.start()
        return thr

    def open_client(self, host: str, tcp_port: int, udp_port: int) -> Thread:
        if host == DEFAULT_IP:
            host = DEFAULT_CLIENT_BIND
        thr = Thread(target=self.network_socket.client_connect_func, args=(host, tcp_port, udp_port))
        thr.daemon = True
        thr.start()
        return thr

    def tcp_recv_thread(self, tcp_txt_box) -> None:
        def tcp_recv_data():
            tcp_delayed_buffer = None
            while self.tcp_thr_flag:
                try:
                    if tcp_delayed_buffer:
                        data = tcp_delayed_buffer
                    else:
                        data = self.network_socket.tcp_recv()

                    while len(data) < PACKET_SIZE + APP_HEADER_LEN:
                        data = data + self.network_socket.tcp_recv()

                    if len(data) > PACKET_SIZE + APP_HEADER_LEN:
                        tcp_delayed_buffer = data[PACKET_SIZE + APP_HEADER_LEN:]
                        data = data[:PACKET_SIZE + APP_HEADER_LEN]
                    else:
                        tcp_delayed_buffer = None

                    if len(data) > 0:
                        app_header = data[:APP_HEADER_LEN]
                        app_data = data[APP_HEADER_LEN:]
                        if app_header == TYPE_TEXT_MSG:
                            data_len = struct.unpack(">H", app_data[:2])[0]
                            app_data = app_data[2:2+data_len]
                            text = app_data.decode(ENCODING)
                            tcp_txt_box.insert(END, time.strftime("(recv) %H:%M -> ") + text)
                            tcp_txt_box.update()
                        elif app_header == TYPE_FILE_TRANSFER:
                            cpl_flag = self.file_transper.tcp_file_receive(app_data)
                            if cpl_flag == 0:
                                tcp_txt_box.insert(END, time.strftime("(file recv start) %H:%M\n"))
                                tcp_txt_box.update()
                            
                            elif cpl_flag == 2:
                                tcp_txt_box.insert(END, time.strftime("(file recv end) %H:%M\n"))
                                self.file_transper.file_name = None
                                tcp_txt_box.update()
                except OSError:
                    break
        self.tcp_thr_flag = True
        self.tcp_box_thread = Thread(target=tcp_recv_data)
        self.tcp_box_thread.daemon = True
        self.tcp_box_thread.start()

    def udp_recv_thread(self, udp_txt_box) -> None:
        def udp_recv_data():  # add delayed buffer???
            udp_delayed_buffer = None
            while self.udp_thr_flag:
                try:
                    if udp_delayed_buffer:
                        data = udp_delayed_buffer
                    else:
                        data = self.network_socket.udp_recv()
                    while len(data) < PACKET_SIZE + APP_HEADER_LEN:
                        data = data + self.network_socket.udp_recv()
                    if len(data) > PACKET_SIZE + APP_HEADER_LEN:
                        udp_delayed_buffer = data[PACKET_SIZE + APP_HEADER_LEN:]
                        data = data[:PACKET_SIZE + APP_HEADER_LEN]
                    else:
                        udp_delayed_buffer = None

                    app_header = data[:APP_HEADER_LEN]
                    app_data = data[APP_HEADER_LEN:]
                    if len(data) > 0:
                        if app_header == TYPE_TEXT_MSG:
                            data_len = struct.unpack(">H", app_data[:2])[0]
                            app_data = app_data[2:2+data_len]
                            text = app_data.decode(ENCODING)
                            udp_txt_box.insert(END, time.strftime("(recv) %H:%M -> ") + text)
                            udp_txt_box.update()
                        elif app_header == TYPE_FILE_TRANSFER:
                            cpl_flag = self.file_transper.udp_file_receive(app_data, self.udp_file_transfer_send)
                            if cpl_flag == 0:
                                udp_txt_box.insert(END, time.strftime("(file recv start) %H:%M\n"))
                                self.file_transper.file_name = None
                                udp_txt_box.update()
                            elif cpl_flag == 2:
                                udp_txt_box.insert(END, time.strftime("(file recv end) %H:%M\n"))
                                self.file_transper.file_name = None
                                udp_txt_box.update()
                            
                except OSError:
                    break
        self.udp_thr_flag = True
        self.udp_box_thread = Thread(target=udp_recv_data)
        self.udp_box_thread.daemon = True
        self.udp_box_thread.start()

    def send_msg_func(self, send_opt: int, msg: str) -> None:
        data = msg.encode(ENCODING)

        while data:
            if len(data) > PACKET_SIZE - 2:
                send_data = data[:PACKET_SIZE-2]
                data = data[PACKET_SIZE-2:]
            else:
                send_data = data
                data = None
            len_data = len(send_data)
            if len_data < PACKET_SIZE-2:
                send_data = send_data + bytes(PACKET_SIZE - 2 - len_data)
            
            send_data = TYPE_TEXT_MSG + struct.pack(">H", len_data) + send_data

            if send_opt in (0, 2):
                self.network_socket.tcp_send(send_data)
            if send_opt in (1, 2):
                self.network_socket.udp_send(send_data)
    
    def tcp_file_transfer_send(self, packet):
        # 캡슐화
        packet = TYPE_FILE_TRANSFER + packet
        self.network_socket.tcp_send(packet)

    def udp_file_transfer_send(self, packet):
        packet = TYPE_FILE_TRANSFER + packet
        self.network_socket.udp_send(packet)

    def send_file_func(self, send_opt: int, filename: str, tcp_txt_box, udp_txt_box) -> None:
        if send_opt == 0:
            tcp_txt_box.insert(END, time.strftime("(file send start) %H:%M\n"))
            tcp_txt_box.update()
            self.file_transper.tcp_file_send(filename, tcp_send_func=self.tcp_file_transfer_send)
            tcp_txt_box.insert(END, time.strftime("(file send end) %H:%M\n"))
            tcp_txt_box.update()
        elif send_opt == 1:
            udp_txt_box.insert(END, time.strftime("(file send start) %H:%M\n"))
            udp_txt_box.update()
            self.file_transper.udp_file_send(filename, udp_send_func=self.udp_file_transfer_send)
            udp_txt_box.insert(END, time.strftime("(file send end) %H:%M\n"))
            udp_txt_box.update()
        else:
            tcp_txt_box.insert(END, time.strftime("(file send start) %H:%M\n"))
            tcp_txt_box.update()
            self.file_transper.tcp_file_send(filename, tcp_send_func=self.tcp_file_transfer_send)
            tcp_txt_box.insert(END, time.strftime("(file send end) %H:%M\n"))
            tcp_txt_box.update()
            sleep(1.)
            udp_txt_box.insert(END, time.strftime("(file send start) %H:%M\n"))
            udp_txt_box.update()
            self.file_transper.udp_file_send(filename, udp_send_func=self.udp_file_transfer_send)
            udp_txt_box.insert(END, time.strftime("(file send end) %H:%M\n"))
            udp_txt_box.update()

    def close(self):
        self.tcp_thr_flag = False
        self.udp_thr_flag = False
        self.network_socket.close()
