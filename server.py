import socket
import threading
import struct
import time
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
                server_socket.close()
                print('客户端'+str(client.getpeername())+'已退出')
                break
            if feedback!=1:
                clientrv, rvD_addr = server_list[1].accept()
                clientsv, svD_addr = server_list[2].accept()
                meets[info[1]]['rvc'].append(clientrv)
                meets[info[1]]['svc'].append(clientsv)
                print('客户端视频发送通道已连接,客户端socket：'+str(clientsv))
                print('客户端视频接收通道已连接,客户端socket：'+str(clientrv))
                if feedback==2:
                    threading.Thread(target=meeting_video,args=(info[1],)).start()
        except ConnectionResetError or struct.error:
            clients.remove(client)
            server_socket.close()
            for meet in meets.keys():
                if meets[meet]['origin'] == client:
                    meets.pop(meet)
                elif client in meets[meet]['member']:
                    meets[meet]['member'].remove(client)
            print('客户端' + str(client.getpeername()) + '已退出')
            break


def meeting_video(meetnum):
    meet=meets[meetnum]
    print(meet)
    while True:
        i=0
        for client_rv in meet['rvc']:
            data = b""
            i=i+1
            begin=struct.unpack('c',client_rv.recv(1))
            print('收到begin'+str(begin))
            while True:
                if begin[0] == b'B':
                    begin = struct.unpack('c', client_rv.recv(1))
                    print('收到begin' + str(begin[0]))
                    if begin[0] == b'C':
                        break
                    elif begin[0] != b'B':
                        e = client_rv.recv(20000)
                        print('错误信息长度：' + str(len(e)))
                        begin = struct.unpack('c', client_rv.recv(1))
                        print('收到begin' + str(begin[0]))
                elif begin[0] != b'B':
                    e=client_rv.recv(20000)
                    print('错误信息长度：'+str(len(e)))
                    begin = struct.unpack('c', client_rv.recv(1))
                    print('收到begin' + str(begin[0]))
            info=struct.unpack('L',client_rv.recv(4))
            print('客户端：'+str(i)+'数据长度:'+str(info[0]))
            data+=client_rv.recv(info[0])
            for client_sv in meet['svc']:
                if client_sv.getpeername()[0]==client_rv.getpeername()[0]:
                    continue
                client_sv.send(struct.pack('ccc', b'B',b'B',b'C'))
                print('发送数据长度：'+str(len(data)))
                client_sv.send(struct.pack('LL',len(data),i))
                client_sv.sendall(data)


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

