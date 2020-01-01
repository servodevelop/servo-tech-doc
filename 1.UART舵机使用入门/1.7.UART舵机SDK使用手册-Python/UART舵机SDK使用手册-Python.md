
# UART舵机SDK使用手册-Python

[toc]

## 测试平台

测试所用到的软件开发环境与硬件开发平台

* 操作系统 `Ubuntu16.04`
* Python版本号 `Python3.6`
* IDE:  `Jupyter Notebook`
* Fashion Star 串口舵机 x2
* 二自由度云台支架 (可选)




**注意事项**
1. **代码兼容Windows**，但是需要改一下设备号*确定串口设备号* 中的`USERVO_PORT_NAME`

2. 关于Python的版本：Python3.5以及以上都兼容

3. 使用Jupyter Notebook的原因是可以方便 Python 脚本的交互测试，可以做到执行一条语句，舵机响应一下动作。
   还可以看到每执行一条指令，串口舵机发送与接收的所有字节数据。
   
   用Jupyter Notebook打开`src/串口舵机测试.ipynb` 
   
4. 二自由度云台支架只在*设置舵机的控制流* 中用到，演示效果更好，不用也可以。



## 安装依赖


测试串口舵机只依赖一个库文件`pyserial`


Windows/Ubuntu/树莓派下可以直接通过命令行安装
```bash
pip3 install pyserial
```



## 导入依赖


```python
import time
import subprocess
import logging
import serial
import struct
# 导入串口舵机管理器
# 将fs_uservo.py放置到该脚本的同级目录下
from fs_uservo import UartServoManager
```



## 设置日志输出模式


```python
# 设置日志输出模式为INFO
logging.basicConfig(level=logging.INFO)
```



## 确定串口设备号

设置串口舵机转接板的设备端口号



### Windows

Windows平台下，端口号以`COM`开头，例如`COM8`。

```python
## 如果是Windows操作系统　串口设备号
USERVO_PORT_NAME = 'COM8'
```
端口号可以通过Windows的设备列表查看，或者通过串口舵机的调试软件查看。

详情见*FashionStar串口舵机说明书 // 舵机调试软件 // 串口连接*



### Linux

Linux平台下，端口号以`/dev/ttyUSB`开头，例如`/dev/ttyUSB0`。

获取设备号的脚本：
```bash
ls /dev/ttyUSB*
```
日志就会列出`/dev/ttyUSB`开头的所有设备号。
```
/dev/ttyUSB0
```

**注意事项**

1. 需要注意的是，端口号不一定是固定的。例如连接串口舵机的USB拔下又插上，端口号可能就会发生变动。
2. 下方的设备号自动获取的代码只适用于Linux操作系统。

填写/修改设备号


```python
USERVO_PORT_NAME = ''
## 如果是Windows操作系统　串口设备号
# USERVO_PORT_NAME = 'COM8'

## Linux开发平台 串口设备号
# USERVO_PORT_NAME = '/dev/ttyUSB0'
```


```python
# 如果设备号没有制定, 在Linux平台下,自动进行端口扫描
if len(USERVO_PORT_NAME) == 0:
    # Linux平台下自动查询串口舵机转接板的设备号
    res = subprocess.Popen("ls /dev/ttyUSB*",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)  
    # 获取设备列表
    device_list = res.stdout.read().decode('utf-8').split()
    if len(device_list) == 0:
        logging.warn('[Error]请插入串口舵机转接板, 或检查电源')
        exit(-1)
    # 始终选择最后插入的那个设备
    USERVO_PORT_NAME = max(device_list, key=lambda d: d[-1]) 
    logging.info('识别串口舵机的端口号: {}'.format(USERVO_PORT_NAME))
```

    INFO:root:识别串口舵机的端口号: /dev/ttyUSB0



## 创建串口对象

串口通信的配置

| 参数名称(en) | 参数名称(cn) | 参数数值 | 备注                                                         |
| ------------ | ------------ | -------- | ------------------------------------------------------------ |
| baudrate     | 波特率       | 115200   | |
| parity       | 奇偶校验     | 无       |                                                              |
| stopbits     | 停止位       | 1        |                                                              |
| bytesize     | 字节长度     | 8        |                                                              |

详情参见 *串口通信协议  / 舵机通信协议 / 串口通信配置*


```python
# 创建串口对象
uart = serial.Serial(port=USERVO_PORT_NAME, baudrate=115200,\
                     parity=serial.PARITY_NONE, stopbits=1,\
                     bytesize=8,timeout=0)
```



## 创建串口舵机管理器


**函数** 

`UartServoManager(uart, srv_num=1, mean_dps=100)` 

**功能**

创建串口舵机管理器。

**参数**

* @param `uart` 串口对象
* @param `srv_num` 代表串联的舵机的个数，而且是默认从`0x00`开始依次递增 
* @param `mean_dps` 默认的舵机角速度，单位 °/s，默认为100°/s

在创建串口舵机管理器时，会给每个舵机发送舵机通讯检测指令`PING`。

如果舵机回传数据，则认为舵机是有效的，若舵机超时没有应答，则认为舵机不在线，抛出警告信息。

详情见 *串口通信协议 / <指令>舵机通讯检测*


```python
# 这里因为我们的测试平台是2DoF的舵机云台
# 如果没有第二个舵机的话 会有一个Error信息提示
# ERROR:root:[fs_uservo]串口舵机ID=1 掉线, 请检查
srv_num = 2 # 舵机个数
uservo_manager = UartServoManager(uart, srv_num=srv_num)
```

    INFO:root:串口发送请求数据 code:1
    INFO:root:数据帧内容:
    INFO:root:0x12 0x4c 0x01 0x01 0x00 0x60 
    INFO:root:PING 舵机 id=0
    INFO:root:Recv Bytes: 
    INFO:root:0x05 0x1c 0x01 0x01 0x00 0x23
    INFO:root:[fs_uservo]ECHO 已知舵机 id=0
    INFO:root:[fs_uservo]串口舵机ID=0 响应ping
    INFO:root:串口发送请求数据 code:1
    INFO:root:数据帧内容:
    INFO:root:0x12 0x4c 0x01 0x01 0x01 0x61 
    INFO:root:PING 舵机 id=1
    INFO:root:Recv Bytes: 
    INFO:root:
    ERROR:root:[fs_uservo]串口舵机ID=1 掉线, 请检查



## 设置舵机角度

### API说明

**函数**

`uservo_manager.request_set_srv_angle(srv_id, angle, interval=None, mean_dps=None, power=0)`

**功能**

设定舵机的角度

**参数**
* @param `srv_id` 舵机的ID号
* @param `angle` 舵机的目标角度，角度取值范围 [-135, 135]
* @param `interval` 设置舵机从当前角度运动到目标角度所需要的时间，单位ms
* @param `mean_dps` 指定舵机从当前角度运动到目标角度期间的平均角速度，单位 °/s。`mean_dps` 会被折算成`interval`

**注意事项**

1. 当`interval`和`mean_dps`均不设置时，SDK将会按照`15ms`一度，折算成`interval`。
2. 如果是第一次设置角度，SDK会将第一次角度设置的周期`interval`设置为`800ms`。
3. 关于舵机角度设置的详细介绍，参见*FashionStar串口舵机说明书 / <指令>读取舵机角度*



### 使用示例

#### 设置舵机角度
设置舵机角度（使用默认的角速度）


```python
servo_id = 0 # 舵机ID
angle = 0 # 目标角度
uservo_manager.request_set_srv_angle(0, 0)
```

    INFO:root:串口发送请求数据 code:8
    INFO:root:数据帧内容:
    INFO:root:0x12 0x4c 0x08 0x07 0x00 0x00 0x00 0x20 0x03 0x00 0x00 0x90 



#### 设置舵机角度（指定角速度）
设置舵机的旋转角速度`mean_dps` 来控制舵机。


```python
servo_id = 0 # 舵机ID
angle = 90 # 目标角度
mean_dps = 60 # 平均角速度 
uservo_manager.request_set_srv_angle(servo_id, angle, mean_dps=mean_dps)
```

    INFO:root:串口发送请求数据 code:8
    INFO:root:数据帧内容:
    INFO:root:0x12 0x4c 0x08 0x07 0x00 0x84 0x03 0x00 0x00 0x00 0x00 0xf4 



#### 设置舵机角度（指定周期）
直接设置周期`interval`, 例如设置为100ms.


```python
servo_id = 0 # 舵机ID
angle = 0 # 目标角度
interval = 100 # 运行周期
uservo_manager.request_set_srv_angle(0, 0, interval=100)
```

    INFO:root:串口发送请求数据 code:8
    INFO:root:数据帧内容:
    INFO:root:0x12 0x4c 0x08 0x07 0x00 0x00 0x00 0x64 0x00 0x00 0x00 0xd1 



## 串口舵机信息 UartServoInfo

`UartServoManager`类，有一个属性是`srv_info_dict`。这个`srv_info_dict`是一个字典格式的数据类型。

我们可以通过舵机的ID号来获取对应的串口舵机信息对象（`UartServoInfo`）。

```python
servo_id = 0 # 舵机ID

uservo_manager.srv_info_dict[servo_id]
```

*输出日志*


    <fs_uservo.UartServoInfo at 0x7f2a983dbdd8>



在Python的`SDK`里面舵机的角度是按照指令发出时间，以及时间周期来对角度做一个近似估算。

获取舵机当前所在的角度需要通过`.angle`属性


```python
uservo_manager.srv_info_dict[servo_id].angle
```

*输出日志*


    0



舵机当前是否在运动中，需要访问`is_stop()`方法，返回一个布尔值。

* `True` 舵机已经停止
* `False` 舵机正在旋转


```python
uservo_manager.srv_info_dict[servo_id].is_stop()
```

*输出日志*


    True



另外`UartServoManager`也有一个`is_stop()`方法，它返回的是所有的舵机是否停止


```python
uservo_manager.is_stop()
```

*输出日志*


    True



## 设置舵机的控制流

在很多PID舵机角度设置/自稳云台等应用，可以不停的给舵机云台发送控制指令, 而不需要每次都等待舵机执行到目标角度。

但在有些应用场景下面，例如机械臂，我们需要让机械臂按照某个操作流程完成一个任务，舵机/舵机序列是先旋转到一个角度，然后再旋转到下一个角度。
有严格的时序关系。


比较简单的写法是通过`UartServoManager`的`is_stop`方法，还有`while`循环来实现，这是最简单的实现方法。

当然你也可以通过多线程/多进程的方式进行编程。


```python
import time # 导入时间模块

# 定义一个等待舵机旋转完毕的函数
def uservo_wait():
    global uservo_manager
    while True:
        if uservo_manager.is_stop():
            break
        # 等待10ms
        time.sleep(0.01)

```

**示例** 舵机设置序列延时（单个舵机）


```python
servo_id = 0
uservo_manager.mean_dps = 200 # 修改平均角速度
uservo_manager.request_set_srv_angle(servo_id, 0)
# -----这里可以添加对其他舵机/关节角度的设置------
# -----角度都设置完成之后,再一起等待-------
uservo_wait() # 等待角度设置结束

uservo_manager.request_set_srv_angle(servo_id, 90)
uservo_wait() # 等待角度设置结束

# 关节运动到一个特定的位置之后，可能要停顿一下，执行抓取或者放置的动作
time.sleep(0.5) # 延时0.5s = 500ms

# 不同的动作之间的速度要求可能也都不一样, 可以通过设置全局角速度的方式进行修改
uservo_manager.mean_dps = 100 # 修改平均角速度

uservo_manager.request_set_srv_angle(servo_id, -90) 
uservo_wait() # 等待角度设置结束

uservo_manager.mean_dps = 200 # 修改平均角速度
uservo_manager.request_set_srv_angle(servo_id, 0)
uservo_wait() # 等待角度设置结束
```

    INFO:root:串口发送请求数据 code:8
    INFO:root:数据帧内容:
    INFO:root:0x12 0x4c 0x08 0x07 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x6d 
    INFO:root:串口发送请求数据 code:8
    INFO:root:数据帧内容:
    INFO:root:0x12 0x4c 0x08 0x07 0x00 0x84 0x03 0xc2 0x01 0x00 0x00 0xb7 
    INFO:root:串口发送请求数据 code:8
    INFO:root:数据帧内容:
    INFO:root:0x12 0x4c 0x08 0x07 0x00 0x7c 0xfc 0x08 0x07 0x00 0x00 0xf4 
    INFO:root:串口发送请求数据 code:8
    INFO:root:数据帧内容:
    INFO:root:0x12 0x4c 0x08 0x07 0x00 0x00 0x00 0xc2 0x01 0x00 0x00 0x30 

**示例** 舵机设置序列延时（多个舵机）


```python
srv_down = 0 # 云台下部的舵机ID号
srv_up = 1 # 云台上部的舵机的ID号
```


```python
uservo_manager.mean_dps = 200 # 修改平均角速度

# 动作1 初始位
uservo_manager.request_set_srv_angle(srv_down, 0) 
uservo_manager.request_set_srv_angle(srv_up, 0)
uservo_wait() # 等待角度设置结束

# 动作2
uservo_manager.request_set_srv_angle(srv_down, 90)
uservo_manager.request_set_srv_angle(srv_up, 60)
uservo_wait() # 等待角度设置结束

# 关节运动到一个特定的位置之后，可能要停顿一下，执行抓取或者放置的动作
# 这里只是模拟个延时
time.sleep(0.5) # 延时0.5s = 500ms

# 不同的动作之间的速度要求可能也都不一样, 可以通过设置全局角速度的方式进行修改
uservo_manager.mean_dps = 100 # 修改平均角速度

# 动作3
uservo_manager.request_set_srv_angle(srv_down, -90)
uservo_manager.request_set_srv_angle(srv_up, -60)
uservo_wait() # 等待角度设置结束

# 动作4 (初始位)
uservo_manager.mean_dps = 200 # 修改平均角速度
uservo_manager.request_set_srv_angle(srv_down, 0)
uservo_manager.request_set_srv_angle(srv_up, 0)
uservo_wait() # 等待角度设置结束
```

    INFO:root:串口发送请求数据 code:8
    INFO:root:数据帧内容:
    INFO:root:0x12 0x4c 0x08 0x07 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x6d 
    INFO:root:串口发送请求数据 code:8
    INFO:root:数据帧内容:
    INFO:root:0x12 0x4c 0x08 0x07 0x01 0x00 0x00 0x00 0x00 0x00 0x00 0x6e 
    INFO:root:串口发送请求数据 code:8
    INFO:root:数据帧内容:
    INFO:root:0x12 0x4c 0x08 0x07 0x00 0x84 0x03 0xc2 0x01 0x00 0x00 0xb7 
    INFO:root:串口发送请求数据 code:8
    INFO:root:数据帧内容:
    INFO:root:0x12 0x4c 0x08 0x07 0x01 0x58 0x02 0x2c 0x01 0x00 0x00 0xf5 
    INFO:root:串口发送请求数据 code:8
    INFO:root:数据帧内容:
    INFO:root:0x12 0x4c 0x08 0x07 0x00 0x7c 0xfc 0x08 0x07 0x00 0x00 0xf4 
    INFO:root:串口发送请求数据 code:8
    INFO:root:数据帧内容:
    INFO:root:0x12 0x4c 0x08 0x07 0x01 0xa8 0xfd 0xb0 0x04 0x00 0x00 0xc7 
    INFO:root:串口发送请求数据 code:8
    INFO:root:数据帧内容:
    INFO:root:0x12 0x4c 0x08 0x07 0x00 0x00 0x00 0xc2 0x01 0x00 0x00 0x30 
    INFO:root:串口发送请求数据 code:8
    INFO:root:数据帧内容:
    INFO:root:0x12 0x4c 0x08 0x07 0x01 0x00 0x00 0x2c 0x01 0x00 0x00 0x9b 



## 角度回传测试

### API说明

**函数**
```
uservo_manager.request_query_srv_angle(srv_id)
```

**功能**

查询单个舵机的角度

**参数**

* @param `srv_id` 舵机ID

### 使用示例


```python
for srv_id in range(2):
    # 查询舵机的角度
    uservo_manager.request_query_srv_angle(srv_id)
    # 延时10ms
    time.sleep(0.01)

# 批量处理串口缓冲区内接收到的舵机角度反馈信息
uservo_manager.update() # 接收获得的反馈数据
```
查看更新之后的舵机角度

```python
# 查看更新之后的角度数据
print('0号舵机 当前的角度为:')
print(uservo_manager.srv_info_ditc[0].cur_angle)
print('1号舵机 当前的角度为:')
print(uservo_manager.srv_info_ditc[1].cur_angle)
```



## 轮式模式

### API说明
**函数**

`request_set_spin(self, srv_id, mode, value=0, is_cw=True, speed=None)`

**功能**

轮式设置模式

**参数**

* @param `srv_id`
    舵机的ID号
* @param `mode`
    舵机的模式 取值范围[0,3]
* @param `value` 
    定时模式下代表时间(单位ms)
    定圈模式下代表圈数(单位圈)
* ＠param `is_cw`
    轮子的旋转方向, is_cw代表是否是顺指针旋转
* @param `speed`
    轮子旋转的角速度, 单位 度/s

    ​    

轮式模式下舵机控制模式的说明

| 序号(二进制) | 序号(十六进制) | 执行方式                        |
| ------- | -------- | --------------------------- |
| 00      | 0x00     | 舵机停止                        |
| 01      | 0x01     | 舵机持续旋转(不停)                  |
| 10      | 0x02     | 舵机定圈旋转(旋转`value`圈后, 舵机停止)   |
| 11      | 0x03     | 舵机定时旋转(旋转`value` ms后， 舵机停止) |


详情见 *串口通信协议 /  <指令>轮式模式控制*



### 使用示例

**警告: 测试下列例程时请确保关节可以360旋转。对于云台/机械臂，关节是不可以360度旋转的，因为有接线还有机械臂结构的约束。**

如果用的是云台， 可以把舵机1和舵机0的接线断开。

#### 轮子不停的旋转


```python
servo_id = 0 # 舵机ID
mode = UartServoManager.WHEEL_MODE_NORMAL # 设置模式为不停的旋转
uservo_manager.request_set_spin(servo_id, mode, speed=100, is_cw = False)
```

    INFO:root:串口发送请求数据 code:7
    INFO:root:数据帧内容:
    INFO:root:0x12 0x4c 0x07 0x06 0x00 0x01 0x64 0x00 0x00 0x00 0xd0 


测试逆时针旋转


```python
uservo_manager.request_set_spin(servo_id, mode, is_cw = True)
```

    INFO:root:串口发送请求数据 code:7
    INFO:root:数据帧内容:
    INFO:root:0x12 0x4c 0x07 0x06 0x00 0x00 0x64 0x00 0x00 0x00 0xcf 


#### 轮子停止


```python
servo_id = 0 # 舵机ID
mode = UartServoManager.WHEEL_MODE_STOP # 设置模式为不停的旋转
uservo_manager.request_set_spin(servo_id, mode)
```

    INFO:root:串口发送请求数据 code:7
    INFO:root:数据帧内容:
    INFO:root:0x12 0x4c 0x07 0x06 0x00 0x80 0x64 0x00 0x00 0x00 0x4f 


#### 轮子定圈


```python
servo_id = 0 # 舵机ID
mode = UartServoManager.WHEEL_MODE_ROUND # 控制模式
speed = 100 # 旋转速度
nround = 5 # 旋转5圈
is_cw = True # 顺时针运动
uservo_manager.request_set_spin(servo_id, mode, value=nround, speed=speed, is_cw=is_cw)
```

    INFO:root:串口发送请求数据 code:7
    INFO:root:数据帧内容:
    INFO:root:0x12 0x4c 0x07 0x06 0x00 0x82 0x64 0x00 0x05 0x00 0x56 


#### 轮子定时


```python
servo_id = 0 # 舵机ID
mode = UartServoManager.WHEEL_MODE_TIME # 控制模式
speed = 100 # 旋转速度
time_ms = 1000 # 旋转1000ms
is_cw = True # 顺时针运动
uservo_manager.request_set_spin(servo_id, mode, value=time_ms, speed=speed, is_cw=is_cw)
```

    INFO:root:串口发送请求数据 code:7
    INFO:root:数据帧内容:
    INFO:root:0x12 0x4c 0x07 0x06 0x00 0x83 0x64 0x00 0xe8 0x03 0x3d 



## 阻尼模式

### API说明

**函数**

`uservo_manager.request_set_damming(srv_id, power=0)`


**功能**

开启阻尼模式,并设置舵机的保持功率。


**参数**
* @param `srv_id` 舵机的ID
* @param `power` 舵机的保持功率 (单位mW)


**注意事项**
1. 如果保持功率`power`设置为0，或者大于功率上限，则按照功率上限处理。
2. 保持功率越大，阻力越大。

详情见 *串口通信协议  /  <指令> 阻尼模式控制*

### 使用示例

设置0号舵机的阻尼模式的保持功率为500 mW。


```python
servo_id = 0 # 舵机ID
power = 500 # 保持功率
uservo_manager.request_set_damming(servo_id, power)
```

    INFO:root:串口发送请求数据 code:9
    INFO:root:数据帧内容:
    INFO:root:0x12 0x4c 0x09 0x03 0x00 0xf4 0x01 0x5f 

