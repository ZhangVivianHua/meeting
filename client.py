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
        camera = cv2.VideoCapture(0,cv2.CAP_DSHOW)  # 从摄像头中获取视频
        img_param = [int(cv2.IMWRITE_JPEG_QUALITY), 15]  # 设置传送图像格式、帧数
        flag = camera.isOpened()
        while flag:
            _, img = camera.read()  # 读取视频每一帧
            time.sleep(0.01)  # 推迟线程运行0.1s
            if img is None:
                print('没有读到图片')
                continue
            img = cv2.resize(img, (640, 480))  # 按要求调整图像大小(resolution必须为元组)
            _, img_encode = cv2.imencode('.jpg', img, img_param)  # 按格式生成图片
            img_code = numpy.array(img_encode)  # 转换成矩阵
            img_data = img_code.tobytes()  # 生成相应的字符串
            try:
                # 按照相应的格式进行打包发送图片
                send_vsocket.send(struct.pack("ccc", b'B',b'B',b'C'))
                send_vsocket.send(struct.pack("L", len(img_data)))
                print('发送数据长度：'+str(len(img_data)))
                send_vsocket.sendall(img_data)
            except:
                camera.release()


def video_recv():
    recv_vsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    recv_vsocket.connect((ip, recv_vport))
    print('成功连接接收通道')
    while True:
        try:
            buf = b""
            begin = struct.unpack('ccc', recv_vsocket.recv(3))
            print('收到begin' + str(begin))
            while begin[0] != b'B' or begin[1] != b'B' or begin[2] != b'C':
                begin = struct.unpack('ccc', recv_vsocket.recv(3))
                print('收到begin' + str(begin))
            img_info = struct.unpack('LL', recv_vsocket.recv(8))
            print('接收数据长度：'+str(img_info[0]))
            buf += recv_vsocket.recv(img_info[0])
            data = numpy.frombuffer(buf, dtype='uint8')  # 按uint8转换为图像矩阵
            image = cv2.imdecode(data, 1)  # 图像解码
            cv2.imshow('user' + str(img_info[1]), image)
        except:
            pass;
        finally:
            if (cv2.waitKey(1) == 27):  # 每10ms刷新一次图片，按‘ESC’（27）退出
                cv2.destroyAllWindows()
                break


if __name__ == '__main__':
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.connect((ip,state_port))
    print('成功连接服务器')
    threading.Thread(target=connect_server).start()


