from os import chdir
from os.path import split
from RemoteFunction import *


run = True


class C:

    def b(self):
        print(1)


class B:

    def __init__(self):
        self.c = 1
        self.a = C()

    def b(self):
        print(1)


class A(BeingControlSide):

    def __init__(self, s: socket):
        super().__init__(s)
        self.a = B()

    # def a(self):
    #     print(1)

    def stop_main(self):
        global run
        run = False


def main():
    global run
    s = SERVER(10000)
    while run:
        s2 = s.accept(A, '1234567890')  # type: BeingControlSide
        if s2 is None:
            continue
        print('连接成功')
        s2.start()
        s2.run_main.join()
        print('结束连接')


if __name__ == '__main__':
    chdir(split(__file__)[0])
    main()
