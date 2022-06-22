from os import chdir
from os.path import split
from RemoteFunction import *


def main():
    # 在client的第一个空字符串里填入自己的ip
    s1 = client('', 10000, '1234567890')
    if not s1:
        return
    print(s1.a.c)
    s1.a.b()
    print(s1.a.b)
    s1.a.a.b()
    print(s1.a)
    s1.b()


if __name__ == '__main__':
    chdir(split(__file__)[0])
    main()
