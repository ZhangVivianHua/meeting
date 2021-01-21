import socket
import threading
import struct
import time
import datetime
ip='192.168.0.74'
begin_port=8888
SP=0
RV=1
SV=2
RA=3
SA=4
state_port=begin_port+SP
recv_vport=begin_port+RV
send_vport=begin_port+SV
recv_aport=begin_port+RA
send_aport=begin_port+SA
clients=[]
meets={}


def listen_contact():
    while True:
        client, D_addr = server_list[0].accept()
        clients.append(client)
        print('客户端'+str(len(clients))+'已连接,客户端socket：'+str(client))
        print('全部会议：'+str(meets))
        threading.Thread(target=listen_state,args=(client,)).start()


def listen_state(client):
    while True:
        try:
            info=struct.unpack('hh',client.recv(4))
            msg=''
            if info[0] == 1:
                if len(meets)>=3:
                    msg='系统超过3个会议，不能再创建新会议了'
                    feedback=1
                else:
                    msg='用户新建了一个视频会议'+str(info[1])
                    meet={'origin':client,'member':[client,],'rvc':[],'svc':[],'rac':[],'sac':[]}
                    meets[info[1]]=meet
                    feedback=2
            elif info[0]==2:
                msg='用户想要加入一个视频会议'+str(info[1])
                if info[1] in meets.keys():
                    if len(meets[info[1]]['member'])>=5:
                        msg+='\n超过5人，拒绝加入'
                        feedback=1
                    else:
                        meets[info[1]]['member'].append(client)
                        msg+='\n成功加入'
                        feedback=3
                else:
                    msg+='\n该会议不存在！'
                    feedback=1
            else:
                msg='退出系统'
                clients.remove(client)
                feedback=1
            print('('+str(client.getpeername())+')'+msg)
            client.sendall(msg.encode())
            client.sendall(struct.pack('h',feedback))
            if info[0] != 1 and info[0] != 2:
                client.close()
                print('客户端'+str(client.getpeername())+'已退出')
                break
            if feedback!=1:
                clientrv, rvD_addr = server_list[1].accept()
                clientsv, svD_addr = server_list[2].accept()
                clientra, raD_addr = server_list[3].accept()
                clientsa, saD_addr = server_list[4].accept()
                meets[info[1]]['rvc'].append(clientrv)
                meets[info[1]]['svc'].append(clientsv)
                meets[info[1]]['rac'].append(clientra)
                meets[info[1]]['sac'].append(clientsa)
                print('客户端视频发送通道已连接,客户端socket：'+str(clientsv))
                print('客户端视频接收通道已连接,客户端socket：'+str(clientrv))
                print('客户端音频发送通道已连接,客户端socket：' + str(clientsa))
                print('客户端音频接收通道已连接,客户端socket：' + str(clientra))
                if feedback==2:
                    threading.Thread(target=meeting_video,args=(info[1],)).start()
                threading.Thread(target=meeting_audio, args=(info[1], clientra, clientsa)).start()
        except ConnectionResetError or struct.error:
            clients.remove(client)
            print('客户端' + str(client.getpeername()) + '已退出')
            try:
                for meet in meets.keys():
                    if meets[meet]['origin'] == client:
                        meets.pop(meet)
                    elif client in meets[meet]['member']:
                        meets[meet]['member'].remove(client)
                        for member in meets[meet]['member']:
                            member.send(('客户端' + str(client.getpeername()) + '已退出').encode())
            except RuntimeError:
                pass
            client.close()
            print('客户端线程结束')
            break


def meeting_video(meetnum):
    meet=meets[meetnum]
    print(meet)
    while True:
        # print('视频进行中')
        i=0
        if len(meet['rvc'])==0 and len(meet['svc'])==0 or meetnum not in meets.keys():
            msg = '会议' + str(meetnum) + '视频结束'
            print(msg)
            if meetnum in meets:
                meets.pop(meet)
            break
        for client_rv in meet['rvc']:
            try:
                data = b""
                i=i+1
                begin=struct.unpack('c',client_rv.recv(1))
                #print('收到begin'+str(begin))
                while True:
                    if begin[0] == b'B':
                        begin = struct.unpack('c', client_rv.recv(1))
                        #print('收到begin' + str(begin[0]))
                        if begin[0] == b'C':
                            break
                        elif begin[0] != b'B':
                            e = client_rv.recv(20000)
                            print('错误信息长度：' + str(len(e)))
                            begin = struct.unpack('c', client_rv.recv(1))
                            #print('收到begin' + str(begin[0]))
                    elif begin[0] != b'B':
                        e=client_rv.recv(20000)
                        print('错误信息长度：'+str(len(e)))
                        begin = struct.unpack('c', client_rv.recv(1))
                        print('收到begin' + str(begin[0]))
                info=struct.unpack('h',client_rv.recv(2))
                # print('客户端：'+str(client_rv.getpeername())+'数据总长度:'+str(info[0]))
                data+=client_rv.recv(info[0])
                while len(data)<info[0]:
                    # print('本次接收到'+str(len(data))+',再次尝试接收')
                    data+=client_rv.recv(info[0]-len(data))
            except ConnectionResetError or struct.error:
                meets[meetnum]['rvc'].remove(client_rv)
                print('客户端视频接收通道连接错误')
                data=b""
            for client_sv in meet['svc']:
                try:
                    bol=client_sv.getpeername()[0]==client_rv.getpeername()[0]
                    if bol:
                        continue
                    client_sv.send(struct.pack('cc',b'B',b'C'))
                    # print('发送数据长度：'+str(len(data)))
                    client_sv.send(struct.pack('hh',len(data),i))
                    client_sv.sendall(data)
                except ConnectionResetError or struct.error or OSError:
                    meets[meetnum]['svc'].remove(client_sv)
                    print('客户端视频发送通道连接错误')


def meeting_audio(meetnum,client_ra,client_sac):
    meet = meets[meetnum]
    print(meet)
    while True:
        print('音频进行中')
        if len(meet['rac'])==0 and len(meet['sac'])==0 or meetnum not in meets.keys():
            msg = '会议' + str(meetnum) + '音频结束'
            print(msg)
            break
        try:
            packed_size = client_ra.recv(struct.calcsize("L"))
            msg_size = struct.unpack("L", packed_size)[0]
            print(str(datetime.datetime.now().time())+'预接收音频长度：'+str(msg_size))
            data = client_ra.recv(msg_size)
            while len(data) < msg_size:
                print('接收到' + str(len(data)) + ',继续接收')
                data += client_ra.recv(msg_size - len(data))
            print('收到音频长度：'+str(len(data)))
        except ConnectionResetError or struct.error:
            meets[meetnum]['rac'].remove(client_ra)
            print('客户端音频接收通道连接错误')
            data=b"a"
        for client_sa in meet['sac']:
            if data is not None:
                try:
                    bol=client_sa is client_sac
                    if bol:
                        continue
                    client_sa.sendall(struct.pack("L", len(data)))
                    client_sa.sendall(data)
                except ConnectionResetError or struct.error or OSError:
                    meets[meetnum]['sac'].remove(client_sa)
                    print('客户端音频发送通道连接错误')


if __name__ == '__main__':
    port_list=[state_port,recv_vport,send_vport,recv_aport,send_aport]
    mylock = threading.Lock()
    server_list=[]
    for i in range(0,5):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)   # 服务器socket视频实例
        server_socket.bind((ip, int(port_list[i]))) # 服务器视频实例绑定端口和ip
        server_socket.listen()              # 服务器视频实例开始监听ip和端口
        server_list.append(server_socket)
    print(server_list)
    threading.Thread(target=listen_contact).start()

