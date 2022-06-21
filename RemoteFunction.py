"""
本模块目前可以进行远程函数调用，远程变量获取、修改、删除，方法和正常的函数调用一样
"""


from socket import socket, AF_INET, SOCK_STREAM, SO_REUSEADDR, SOL_SOCKET
from time import time, sleep
from threading import Thread
from json import loads, dumps
from typing import Union


# 注：暂未完成模式开发
# READ_ONLY = 'READ_ONLY'  # 只读模式
# SECURITY = 'SECURITY'  # 安全模式
# TRUST = 'TRUST'  # 信任模式
# SYSDBA = 'SYSDBA'  # 最高权限模式
# modules = ['READ_ONLY', 'SECURITY', 'TRUST', 'SYSDBA']
# # READ_ONLY:   只读模式         该模式可以获取子类公有变量
# # SECURITY:    安全模式         该模式可以获取、修改、删除子类公有变量(不包括单下划线开头的)
# # TRUST:       信任模式         该模式可以获取、修改、删除任意子类变量(不包括基类变量)
# # SYSDBA:      最高权限模式      该模式可以获取、修改、删除任意变量
# # 所有模式都可以调用类方法


class SendAllTypeError(Exception):
    """发送完整数据时数据类型不对"""

    def __init__(self, error):
        """发送完整数据时数据类型不对

        :param error: 发送的数据
        """
        self.error = error

    def __str__(self):
        return f'无效的类型{type(self.error).__name__}'


def sendall(s: socket, data: Union[bytes, str, list, dict]):
    """发送完整数据

    :param s: 套接字
    :param data: 数据(可以是str,bytes,list,dict)
    """
    if type(data) == bytes:
        end = b'\1'
    elif type(data) == str:
        data = data.encode('utf-8')
        end = b'\2'
    elif type(data) in [list, dict]:
        data = dumps(data, indent=None, separators=(',', ':')).encode('utf-8')
        end = b'\3'
    else:
        raise SendAllTypeError(data)
    i = -1024
    for i in range(0, len(data) - 1024, 1024):
        s.send(data[i: i + 1024] + b'\0')
    s.send(data[i + 1024:] + end)


def recv(s: socket, timeout: Union[int, None] = 10) -> Union[bytes, str, list, dict]:
    """获取完整数据

    :param s: 套接字
    :param timeout: 超时时间
    :return: 获取的数据
    """
    s.settimeout(timeout)
    data = b''
    while True:
        n = s.recv(1025)
        if n:
            data += n[:-1]
            if n[-1] != 0:
                if n[-1] == 2:
                    data = str(data, 'utf-8')
                elif n[-1] == 3:
                    data = loads(str(data, 'utf-8'))
                break
    return data


class LongRangeError(Exception):
    """远程端出现错误"""

    def __init__(self, error):
        """远程端出现错误

        :param error: 错误信息
        """
        self.error = error

    def __str__(self):
        return self.error


class StrOperate:
    """通过字符串进行操作的基类"""

    # class ModuleNotInModules(Exception):
    #
    #     def __init__(self, error):
    #         self.error = error
    #
    #     def __str__(self):
    #         return f'模式{self.error}不存在'
    #
    # def __init__(self, module):
    #     if module in modules:
    #         self.__module = module
    #     else:
    #         raise self.ModuleNotInModules(module)

    def get_attr(self, name):
        """获取变量的值或方法的对象

        :param name: 变量名或方法名(当有变量名等于方法名时，方法将会被变量覆盖)
        :return: 变量的值或方法的对象
        """
        if name in self.__dict__:
            return self.__dict__[name]
        else:
            try:
                return getattr(self, name)
            except AttributeError:
                raise NameError(f"name '{name}' is not defined")

    def set_attr(self, name, value):
        """设置变量的值

        :param name: 变量的名称
        :param value: 要设置的值
        """
        self.__dict__[name] = value

    def del_attr(self, name):
        """删除变量

        :param name: 变量的名称
        """
        del self.__dict__[name]

    def transfer(self, name, *args, **kwargs):
        """调用方法

        :param name: 方法名称(当有变量名等于方法名时，方法将会被变量覆盖)
        :param args: 方法参数
        :param kwargs: 方法参数
        :return: 方法返回值
        """
        n = getattr(self, name, None)
        if n is not None:
            n = n(*args, **kwargs)
            return n
        else:
            if name in self.__dict__:
                return self.__dict__[name](*args, **kwargs)
            raise NameError(f"name '{name}' is not defined")


class BeingControlSide(StrOperate):
    """被控制端"""

    def __init__(self, s: socket):
        """被控制端

        :param s: 套接字
        """
        self.s = s
        self.run_go = False
        self.run_main = None

    def __del__(self):
        self.run_go = False
        self.s.close()

    def start(self):
        """开始监听控制端事件"""
        self.run_go = True
        self.run_main = Thread(target=self.__run)
        self.run_main.start()

    def __run(self):
        """监听主程序"""
        self.s.setblocking(False)
        while self.run_go:
            try:
                n = recv(self.s)
            except BlockingIOError:
                continue
            if n:
                # print(str(n, 'utf-8'))
                # n = loads(n)
                try:
                    n = self.transfer(n['module'], *n.get('args', []), **n.get('kwargs', {}))
                    if isinstance(n, (dict, list, tuple, str, int, float, bool)) or n is None:
                        n = {'module': 'return', 'args': n}
                    else:
                        n = {'module': 'call', 'args': n.__name__}
                except BaseException as e:
                    n = {'module': 'error', 'args': f'{e.__class__.__name__}: {e}'}
                sendall(self.s, n)

    def _stop(self):
        """结束监听"""
        self.run_go = False
        self._stop_main()

    def _stop_main(self):
        pass

    def stop(self):
        """结束监听，并等待程序结束"""
        self.run_go = False
        if type(self.run_main) == Thread:
            self.run_main.join()

    def __return_data(self, n):
        """处理反馈的数据

        :param n: 数据
        :return: 返回值(如果反馈的数据是错误，则报错)(如果反馈的数据是函数调用，则调用函数并反馈返回值或错误)
        """
        if n['module'] == 'return':
            return n['args']
        elif n['module'] == 'error':
            raise LongRangeError(n['args'])
        else:
            n_ = getattr(self, n['module'], None)
            if n_ is None:
                if n['module'] in self.__dict__:
                    try:
                        n = {'module': 'return',
                             'arg': self.__dict__[n['module']](*n.get('args', []), **n.get('kwargs', {}))}
                    except BaseException as e:
                        n = {'module': 'error', 'args': f'{e.__class__.__name__}: {e}'}
                else:
                    n = {'module': 'error', 'args': f"NameError: name '{n['module']}' is not defined"}
            else:
                n = {'module': 'return',
                     'arg': getattr(self, n['module'])(*n.get('args', []), **n.get('kwargs', {}))}
            sendall(self.s, n)
            return self.__return_data(recv(self.s))

    # def print(self, *args, **kwargs):
    #     """在控制端输出
    #
    #     :param args: 参数(与print一样)
    #     :param kwargs: 参数(与print一样)
    #     :return: 返回值(与print一样)
    #     """
    #     sendall(self.s, {'module': 'print', 'args': args, 'kwargs': kwargs})
    #     return self.__return_data(recv(self.s))
    #
    # def input(self, *args, **kwargs):
    #     """在控制端输出
    #
    #     :param args: 参数(与input一样)
    #     :param kwargs: 参数(与input一样)
    #     :return: 返回值(与input一样)
    #     """
    #     sendall(self.s, {'module': 'input', 'args': args, 'kwargs': kwargs})
    #     return self.__return_data(recv(self.s))


class Call:

    def __init__(self, s, name):
        self.name = name
        self.s = s

    def __call__(self, *args, **kwargs):
        sendall(self.s, {'module': self.name, 'args': args, 'kwargs': kwargs})
        n = recv(self.s)
        if n['module'] == 'return':
            return n['args']
        elif n['module'] == 'error':
            raise LongRangeError(n['args'])


class ControlSide:
    """控制端"""

    def __init__(self, s: socket):
        """控制端

        :param s: 套接字
        """
        self.run = False
        self.s = s
        self.run = True

    def __del__(self):
        sleep(0.1)
        sendall(self.s, {'module': '_stop'})
        self.s.close()

    def __control(self, control, *args, **kwargs):
        """发送指令"""
        sendall(self.s, {'module': control, 'args': args, 'kwargs': kwargs})
        return self.__return_data(recv(self.s))

    def __return_data(self, n):
        if n['module'] == 'return':
            return n['args']
        elif n['module'] == 'error':
            raise LongRangeError(n['args'])
        elif n['module'] == 'call':
            return Call(self.s, n['args'])
        # else:
        #     n_ = getattr(self, n['module'], None)
        #     if n_ is None:
        #         if n['module'] in self.__dict__:
        #             try:
        #                 # print(n.get('args', []), n.get('kwargs', {}))
        #                 n = {'module': 'return',
        #                      'arg': self.__dict__[n['module']](*n.get('args', []), **n.get('kwargs', {}))}
        #             except BaseException as e:
        #                 n = {'module': 'error', 'args': f'{e.__class__.__name__}: {e}'}
        #         else:
        #             n = {'module': 'error', 'args': f"NameError: name '{n['module']}' is not defined"}
        #     else:
        #         n = {'module': 'return',
        #              'arg': getattr(self, n['module'])(*n.get('args', []), **n.get('kwargs', {}))}
        #     sendall(self.s, n)
        #     return self.__return_data(recv(self.s))

    def __getattr__(self, item):
        return self.__control('get_attr', item)

    def __setattr__(self, key, value):
        if key == 'run':
            super().__setattr__(key, value)
        else:
            if super().__getattribute__('run'):
                return self.__control('set_attr', key, value)
            else:
                super().__setattr__(key, value)

    def __delattr__(self, item):
        return self.__control('del_attr', item)


class SERVER:
    """被动连接端"""

    def __init__(self, port, backlog=5):
        """被动连接端

        :param port: 端口号
        :param backlog: 最高等待数
        """
        self.s = socket(AF_INET, SOCK_STREAM)
        self.s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.s.bind(('', port))
        self.s.listen(backlog)

    def accept(self, channel, security_function=None,
               socket_timeout=10, accept_time_out=60) -> Union[ControlSide, BeingControlSide]:
        """等待连接

        :param channel:
        :param security_function: 安全验证程序(或字符串,bytes)
                                  (如果 socket_timeout <= 0 ,则将套接字传递给程序,否则将套接字接收到的数据传递给程序)
        :param socket_timeout: 连接到套接字后等待的时间
        :param accept_time_out: 等待连接的超时时间
        :return:
        """
        __time_go = time()
        while True:
            if time() - __time_go >= accept_time_out:
                break
            self.s.settimeout(accept_time_out)
            try:
                s, address = self.s.accept()
            except socket.timeout:
                continue
            # 要验证
            if security_function is not None:
                # 获取数据后验证
                if socket_timeout > 0:
                    s.settimeout(socket_timeout)
                    n = recv(s)
                    # 用验证程序验证
                    if callable(security_function):
                        if security_function(n):
                            sendall(s, b'yes')
                            return channel(s)
                        else:
                            sendall(s, b'no')
                    # 用数据验证
                    else:
                        if security_function == n:
                            sendall(s, b'yes')
                            return channel(s)
                        else:
                            sendall(s, b'no')
                # 完全交给验证程序验证
                else:
                    if security_function(s):
                        sendall(s, b'yes')
                        return channel(s)
                    else:
                        sendall(s, b'no')
            # 不验证，直接通过
            else:
                sendall(s, b'yes')
                return channel(s)
        self.s.settimeout(None)


def client(ip, port, security_function=None, timeout=10, channel=ControlSide) -> Union[ControlSide, BeingControlSide, bool]:
    """连接

    :param ip: 被连接方ip
    :param port: 被连接方端口号
    :param security_function: 安全验证程序(或字符串,bytes)
    :param timeout: 超时时间
    :param channel: 转换的通道
    :return: ControlSide对象(连接成功) 或 False(验证失败) 或 None(返回数据错误)
    """
    s = socket(AF_INET, SOCK_STREAM)
    s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    s.settimeout(timeout)
    s.connect((ip, port))
    sleep(0.25)
    if security_function is not None:
        if callable(security_function):
            sendall(s, security_function())
        else:
            sendall(s, security_function)
    n = recv(s)
    if n == b'yes':
        sleep(0.25)
        return channel(s)
    elif n == b'no':
        s.close()
        return False
    else:
        s.close()
