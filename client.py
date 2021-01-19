import socket
import threading
import struct
import random
import cv2
import pickle
import time
import zlib
import numpy
ip='192.168.43.99'
begin_port=8888
SP=0
SV=1
RV=2
SA=3
RA=4
state_port=begin_port+SP
send_vport=begin_port+SV
recv_vport=begin_port+RV
send_aport=begin_port+SA
recv_aport=begin_port+RA


def connect_server():
    while True:
        print('请选择：1.新建会议2.加入会议3.退出系统')
        choose = int(input('输入：'))
        if choose == 1:
            num = random.randint(0, 10000)
        elif choose == 2:
            num = int(input('请输入会议号：'))
        else:
            num = 0
        server_socket.sendall(struct.pack('ll', choose, num))
        msg = server_socket.recv(200)
        print(msg.decode())
        info=server_socket.recv(4).decode()
        if choose != 1 and choose != 2:
            server_socket.close()
            print('程序结束')
            break
        if info==1:
            continue
        else:
            threading.Thread(target=video_send).start()
            threading.Thread(target=video_recv).start()
            break


def video_send():
    send_vsocket=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    send_vsocket.connect((ip,send_vport))
    print('成功连接发送通道')
    while True:
        cap = cv2.VideoCapture(0)
        while cap.isOpened():
            ret, frame = cap.read()
            data = pickle.dumps(frame)
            zdata = zlib.compress(data, zlib.Z_BEST_COMPRESSION)
            try:
                send_vsocket.sendall(struct.pack("L", len(zdata)) + zdata)
                time.sleep(0.03)
            except:
                break
            cap.read()


def video_recv():
    recv_vsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    recv_vsocket.connect((ip, recv_vport))
    print('成功连接接收通道')
    payload_size = struct.calcsize("LL")
    data = "".encode("utf-8")
    while True:
        while len(data) < payload_size:
            data += recv_vsocket.recv(81920)
        packed_size_num = data[:payload_size]
        data = data[payload_size:]
        msg_size=struct.unpack("LL", packed_size_num)[0]
        num=struct.unpack("LL", packed_size_num)[1]
        while len(data) < msg_size:
            data += recv_vsocket.recv(81920)
        zframe_data = data[:msg_size]
        data = data[msg_size:]
        frame_data = zlib.decompress(zframe_data)
        frame = pickle.loads(frame_data)
        try:
            cv2.imshow('user'+str(num), frame)
        except:
            pass
        if cv2.waitKey(1) & 0xFF == 27:
            break


if __name__ == '__main__':
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.connect((ip,state_port))
    print('成功连接服务器')
    threading.Thread(target=connect_server).start()


