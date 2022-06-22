# RemoteFunction
让远程操作变得简单

本模块为python模块，它除了python内置库(socket, time, threading, json, typing)外没有其他第三方库依赖
导入本库，用本库中的BeingControlSide做父类创建一个类，类中定义的变量，函数就可以被调用和查看了，注意，不要将查看到的变量以为数据在自己这边了，实际上，它还在服务端那边
