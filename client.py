import socket
import threading
import struct
import random
import cv2
import pickle
import time
import numpy
import pyaudio
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
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 8000
RECORD_SECONDS = 0.3
stream = None
p = pyaudio.PyAudio()


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
        server_socket.sendall(struct.pack('hh', choose, num))
        msg = server_socket.recv(200)
        print(msg.decode())
        info=struct.unpack('h',server_socket.recv(2))
        if choose != 1 and choose != 2:
            server_socket.close()
            print('程序结束')
            break
        if info[0]==1:
            continue
        else:
            threading.Thread(target=video_send).start()
            threading.Thread(target=video_recv).start()
            threading.Thread(target=audio_send).start()
            threading.Thread(target=audio_recv).start()
            # threading.Thread(target=server_msg).start()
            break


def video_send():
    send_vsocket=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    send_vsocket.connect((ip,send_vport))
    print('成功连接视频发送通道')
    while True:
        camera = cv2.VideoCapture(0,cv2.CAP_DSHOW)  # 从摄像头中获取视频
        img_param = [int(cv2.IMWRITE_JPEG_QUALITY), 15]  # 设置传送图像格式、帧数
        flag = camera.isOpened()
        while flag:
            _, img = camera.read()  # 读取视频每一帧
            time.sleep(0.1)  # 推迟线程运行0.1s
            if img is None:
                print('没有读到图片')
                continue
            img = cv2.resize(img, (640, 480))  # 按要求调整图像大小(resolution必须为元组)
            _, img_encode = cv2.imencode('.jpg', img, img_param)  # 按格式生成图片
            img_code = numpy.array(img_encode)  # 转换成矩阵
            img_data = img_code.tobytes()  # 生成相应的字符串
            try:
                cv2.imshow('myself', img)
            finally:
                if (cv2.waitKey(1) == 27):  # 每10ms刷新一次图片，按‘ESC’（27）退出
                    cv2.destroyAllWindows()
                    break
            try:
                # 按照相应的格式进行打包发送图片
                send_vsocket.send(struct.pack("cc", b'B',b'C'))
                send_vsocket.send(struct.pack("h", len(img_data)))
                #print('发送数据长度：'+str(len(img_data)))
                send_vsocket.sendall(img_data)
            except:
                camera.release()


def video_recv():
    recv_vsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    recv_vsocket.connect((ip, recv_vport))
    print('成功连接视频接收通道')
    while True:
        try:
            buf = b""
            begin = struct.unpack('c', recv_vsocket.recv(1))
            # print('收到begin' + str(begin))
            while True:
                if begin[0]==b'B':
                    begin = struct.unpack('c', recv_vsocket.recv(1))
                    # print('收到begin' + str(begin[0]))
                    if begin[0]==b'C':
                        break
                    elif begin[0]!=b'B':
                        e=recv_vsocket.recv(20000)
                        print('错误信息长度：'+str(len(e)))
                        begin = struct.unpack('c', recv_vsocket.recv(1))
                        print('收到begin' + str(begin[0]))
                elif begin[0] != b'B':
                    e=recv_vsocket.recv(20000)
                    print('错误信息长度：'+str(len(e)))
                    begin = struct.unpack('c', recv_vsocket.recv(1))
                    print('收到begin' + str(begin[0]))

            img_info = struct.unpack('hh', recv_vsocket.recv(4))
            # print('接收数据长度：'+str(img_info[0]))
            buf += recv_vsocket.recv(img_info[0])
            while len(buf) < img_info[0]:
                # print('本次接收到' + str(len(buf)) + ',再次尝试接收')
                buf += recv_vsocket.recv(img_info[0] - len(buf))
            data = numpy.frombuffer(buf, dtype='uint8')  # 按uint8转换为图像矩阵
            image = cv2.imdecode(data, 1)  # 图像解码
            cv2.imshow('user' + str(img_info[1]), image)
        except:
            print('接收数据出错')
            pass;
        finally:
            if cv2.waitKey(1) == 27:  # 每10ms刷新一次图片，按‘ESC’（27）退出
                cv2.destroyAllWindows()
                break


def audio_recv():
    recv_asocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    recv_asocket.connect((ip, recv_aport))
    print('成功连接音频接收通道')
    while True:
        stream = p.open(format=FORMAT,channels=CHANNELS,rate=RATE,output=True,frames_per_buffer = CHUNK)
        while stream.is_active():
            data = "".encode("utf-8")
            packed_size = recv_asocket.recv(struct.calcsize("L"))
            msg_size = struct.unpack("L", packed_size)[0]
            print('预接收音频长度：'+str(msg_size))
            data+=recv_asocket.recv(msg_size)
            while len(data) < msg_size:
                print('接收到'+str(len(data))+',继续接收')
                data += recv_asocket.recv(msg_size-len(data))
            frames = pickle.loads(data)
            print('播放音频长度：'+str(len(data)))
            for frame in frames:
                stream.write(frame, CHUNK)


def audio_send():
    send_asocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    send_asocket.connect((ip, send_aport))
    print('成功连接音频发送通道')
    while True:
        stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
        while stream.is_active():
            frames = []
            for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
                data = stream.read(CHUNK)
                frames.append(data)
            senddata = pickle.dumps(frames)
            try:
                send_asocket.sendall(struct.pack("L", len(senddata)) + senddata)
                print('发送音频长度：'+str(len(senddata)))
            except:
                print('音频发送出错')


def server_msg():
    while True:
        msg=server_socket.recv(200)
        print(msg.decode())


if __name__ == '__main__':
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.connect((ip,state_port))
    print('成功连接服务器')
    threading.Thread(target=connect_server).start()


