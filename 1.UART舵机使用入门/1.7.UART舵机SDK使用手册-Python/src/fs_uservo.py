'''
Fashion Star Uart Servo Python驱动库
Fashion Star 串口舵机Python库

'''
import time
import logging
import serial
import struct

# 设置日志等级
logging.basicConfig(level=logging.INFO)

class Packet:
    '''数据包'''
    # 使用pkt_type来区分请求数据还是响应数据
    PKT_TYPE_REQUEST = 0 # 请求包
    PKT_TYPE_RESPONSE = 1 # 响应包
    HEADER_LEN = 2 # 帧头校验数据的字节长度
    HEADERS = [b'\x12\x4c', b'\x05\x1c']
    CODE_LEN = 1 # 功能编号长度
    SIZE_LEN = 1 # 字节长度
    CHECKSUM_LEN = 1 # 校验和长度

    @classmethod
    def calc_checksum(cls, code, param_bytes=b'', pkt_type=1):
        '''计算校验和'''
        header = cls.HEADERS[pkt_type]
        return sum(header + struct.pack('<BB', code, len(param_bytes)) + param_bytes) %256

    @classmethod
    def verify(cls, packet_bytes, pkt_type=1):
        '''检验数据是否合法'''
        # 获取帧头
        header = cls.HEADERS[pkt_type]
      
        # 帧头检验
        if packet_bytes[:cls.HEADER_LEN] != cls.HEADERS[pkt_type]:
            return False
        code, size = struct.unpack('<BB', packet_bytes[cls.HEADER_LEN : cls.HEADER_LEN + cls.CODE_LEN + cls.SIZE_LEN])
        
        # 长度校验
        param_bytes = packet_bytes[cls.HEADER_LEN + cls.CODE_LEN + cls.SIZE_LEN : -cls.CHECKSUM_LEN]
        if len(param_bytes) != size:
            return False

        # 校验和检验
        checksum = packet_bytes[-cls.CHECKSUM_LEN]
        # logging.info('实际的Checksum : {} 计算得到的Checksum: {}'.format(checksum, cls.calc_checksum(code , param_bytes, pkt_type=pkt_type)))
        
        # 校验和检查
        if checksum != cls.calc_checksum(code , param_bytes, pkt_type=pkt_type):
            return False
        
        # 数据检验合格
        return True

    @classmethod
    def pack(cls, code, param_bytes=b''):
        '''数据打包为二进制数据'''
        size = len(param_bytes)
        checksum = cls.calc_checksum(code, param_bytes, pkt_type=cls.PKT_TYPE_REQUEST)
        frame_bytes = cls.HEADERS[cls.PKT_TYPE_REQUEST] + struct.pack('<BB', code, size) + param_bytes + struct.pack('<B', checksum)
        return frame_bytes
    
    @classmethod
    def unpack(cls, packet_bytes):
        '''二进制数据解包为所需参数'''
        if not cls.verify(packet_bytes, pkt_type=cls.PKT_TYPE_RESPONSE):
            # 数据非法
            return None
        code = struct.unpack('<B', packet_bytes[cls.HEADER_LEN:cls.HEADER_LEN+cls.CODE_LEN])[0]
        param_bytes = packet_bytes[cls.HEADER_LEN + cls.CODE_LEN + cls.SIZE_LEN : -cls.CHECKSUM_LEN]
        return code, param_bytes

class PacketBuffer:
    '''Packet中转站'''
    def __init__(self, is_debug=True):
        self.is_debug = is_debug
        self.packet_bytes_list = []
        # 清空缓存区域
        self.empty_buffer()
    
    def update(self, next_byte):
        '''将新的字节添加到Packet中转站'''
        # logging.info('[INFO]: next byte: 0x%02x'%next_byte[0])
        if not self.header_flag:
            # 填充头部字节
            if len(self.header) < Packet.HEADER_LEN:
                # 向Header追加字节
                self.header += next_byte
                if len(self.header) == Packet.HEADER_LEN and self.header == Packet.HEADERS[Packet.PKT_TYPE_RESPONSE]:
                    self.header_flag = True
            elif len(self.header) == Packet.HEADER_LEN:
                # 首字节出队列
                self.header = self.header[1:] + next_byte
                # 查看Header是否匹配
                if self.header == Packet.HEADERS[Packet.PKT_TYPE_RESPONSE]:
                    # print('header: {}'.format(self.header))
                    self.header_flag = True
        elif not self.code_flag:
            # 填充Code
            if len(self.code) < Packet.CODE_LEN:
                self.code += next_byte
                if len(self.code) == Packet.CODE_LEN:
                    # print('code: {}'.format(self.code))
                    self.code_flag = True
        elif not self.size_flag:
            # 填充参数尺寸
            if len(self.size) < Packet.SIZE_LEN:
                self.size += next_byte
                if len(self.size) == Packet.SIZE_LEN:
                    self.size_flag = True
                    # 更新参数个数
                    self.param_len = struct.unpack('<B', self.size)[0]
        elif not self.param_bytes_flag:
            # 填充参数
            if len(self.param_bytes) < self.param_len:
                self.param_bytes += next_byte
                if len(self.param_bytes) == self.param_len:
                    self.param_bytes_flag = True
        else:
            # 计算校验和
            # 构建一个完整的Packet
            tmp_packet_bytes = self.header + self.code + self.size + self.param_bytes + next_byte
            
            ret = Packet.verify(tmp_packet_bytes, pkt_type=Packet.PKT_TYPE_RESPONSE)
            
            if ret:
                self.checksum_flag = True
                # 将新的Packet数据添加到中转列表里
                self.packet_bytes_list.append(tmp_packet_bytes)
            
            # 重新清空缓冲区
            self.empty_buffer()
        
    def empty_buffer(self):
        # 数据帧是否准备好
        self.param_len = None
        self.header = b''
        self.header_flag = False
        self.code = b''
        self.code_flag = False
        self.size = b''
        self.size_flag = False
        self.param_bytes = b''
        self.param_bytes_flag = False
    
    def has_valid_packet(self):
        '''是否有有效的包'''
        return len(self.packet_bytes_list) > 0
    
    def get_packet(self):
        '''获取队首的Bytes'''
        return self.packet_bytes_list.pop(0)


class UartServoInfo:
    '''串口舵机的信息'''
    def __init__(self, id):
        self.id = id # 舵机的ID
        self.cur_angle = None # 当前的角度
        self.target_angle = None # 目标角度
        self.start_time = time.time() # 开始运动的时间
        self.interval = 0 # 舵机运动周期
        
        # self.countdown = 0 # 运动倒计时 单位ms (废弃)
        self.is_online = False # 舵机是否在线 
    
    def is_stop(self):
        '''判断舵机是否已经停止'''
        # 角度范围在1度以内则判断为已经到达目标点
        if self.cur_angle == self.target_angle:
            return True
        
        return (time.time() - self.start_time) > (self.interval/1000.0)
    
    @property
    def angle(self):
        # 当前舵机的角度
        if self.is_stop():
            # 角度同步
            self.cur_angle = self.target_angle
            
            return self.target_angle
        else:
            # 估算进度
            ratio = (time.time() - self.start_time) / (self.interval/1000.0)
            # 按照匀速运动的方式进行角度估算
            return self.cur_angle + (self.target_angle - self.cur_angle) * ratio
        
    def move(self, target_angle, interval):
        '''设置舵机的目标角度'''
        # 设置当前的角度
        self.cur_angle = self.angle # 更新旧的角度
        self.interval = interval # 周期 单位ms
        self.start_time = time.time() # 设置开始运动的时间
        self.target_angle = target_angle # 设置当前的角度
        
    def update(self):
        # 同步角度
        if self.is_stop():
            # 检测到已经停止,同步修改cur_angle
            self.cur_angle = self.target_angle
            # 时间间隔设置为0
            self.interval = 0
            
class UartServoManager:
    '''串口舵机管理器'''
    UPDATE_INTERVAL_MS = 10 # ms
    CODE_PING = 1 # 舵机检测
    CODE_QUERY_SERVO_ANGLE = 10 # 查询舵机的角度
    CODE_QUERY_SERVO_INFO = 5 # 查询舵机所有的信息 (未使用)
    CODE_SET_SERVO_ANGLE = 8 # 设置舵机角度
    CODE_SET_SPIN = 7 # 设置轮式模式
    CODE_SET_DAMMING = 9 # 设置阻尼模式
    RESPONSE_CODE_NEGLECT = []

    # 定义轮式控制的四种控制方法
    WHEEL_MODE_STOP = 0x00 # 停止
    WHEEL_MODE_NORMAL = 0x01 # 常规模式
    WHEEL_MODE_ROUND = 0x02 # 定圈
    WHEEL_MODE_TIME = 0x03 # 定时

    def __init__(self, uart, srv_num=1, mean_dps=100):
        self.uart = uart
        self.pkt_buffer = PacketBuffer()
        self.mean_dps = mean_dps # 默认的舵机旋转角速度
        # 存放舵机信息
        self.srv_info_dict = {}
        # 云台一共是三个舵机 编号从0-2
        for srv_idx in range(srv_num):
            self.srv_info_dict[srv_idx] = UartServoInfo(srv_idx)
        
        # 返回的CODE与函数的映射
        self.response_handle_funcs = {
            self.CODE_QUERY_SERVO_ANGLE: self.response_query_srv_angle,
            self.CODE_PING: self.response_ping,
        }
        
        # ping所有的舵机
        for srv_idx in range(srv_num):
            # 发送ping请求
            self.request_ping(srv_idx)
            time.sleep(0.1)
            # 更新缓冲区
            self.update()
            if not self.srv_info_dict[srv_idx].is_online:
                logging.error('[fs_uservo]串口舵机ID={} 掉线, 请检查'.format(srv_idx))
            else:
                logging.info('[fs_uservo]串口舵机ID={} 响应ping'.format(srv_idx))
    
    def send_request(self, code, param_bytes):
        '''发送请数据'''
        packet_bytes = Packet.pack(code, param_bytes)
        self.uart.write(packet_bytes)

        logging.info('串口发送请求数据 code:{}'.format(code))
        logging.info('数据帧内容:')
        logging.info(''.join(['0x%02x ' % b for b in packet_bytes]))

        
    def request_ping(self, srv_id):
        '''发送Ping请求'''
        self.send_request(self.CODE_PING, struct.pack('<B', srv_id))
        
        logging.info('PING 舵机 id={}'.format(srv_id))

    def response_ping(self, param_bytes):
        '''响应PING请求'''
        srv_id, = struct.unpack('<B', param_bytes)
        if srv_id not in self.srv_info_dict:
            self.srv_info_dict[srv_id] = UartServoInfo(srv_id)
            self.srv_info_dict[srv_id].is_online = True # 设置舵机在线的标志位
            logging.info('[fs_uservo]ECHO 添加一个新的舵机 id={}'.format(srv_id))
        else:
            self.srv_info_dict[srv_id].is_online = True # 设置舵机在线的标志位
            logging.info('[fs_uservo]ECHO 已知舵机 id={}'.format(srv_id))
        

    def request_query_srv_angle(self, srv_id):
        '''更新单个舵机的角度'''
        self.send_request(self.CODE_QUERY_SERVO_ANGLE, struct.pack('<B', srv_id))
        # logging.info('查询单个舵机的角度 id={}'.format(srv_id))
            
    def request_query_all_srv_angle(self):
        '''更新所有的舵机角度'''
        for srv_id in self.srv_info_dict:
            self.query_one_srv_angle(srv_id)
    
    def response_query_srv_angle(self, param_bytes):
        '''相应查询单个舵机角度'''
        # 数据解包
        srv_id, angle = struct.unpack('<Bh', param_bytes)
        # 舵机的分辨率是0.1度
        angle /= 10
        
        if srv_id not in self.srv_info_dict:
            # 没有在已知的舵机列表里面
            # 添加一个新的舵机对象
            self.srv_info_dict[srv_id] = UartServoInfo(srv_id, angle)
            self.srv_info_dict[srv_id].is_online = True
            self.srv_info_dict[srv_id].cur_angle = angle
            # logging.info('[fs_uservo]添加一个新的舵机 id={}  角度:{:.2f} deg'.format(srv_id, angle))
        else:
            # 更新当前的角度
            self.srv_info_dict[srv_id].cur_angle = angle
            # logging.info('[INFO] 更新舵机角度 id={}  角度: {:.2f} deg'.format(srv_id, angle))

    def refresh_srv_list(self, max_srv_id=254):
        '''刷新当前的舵机列表'''
        # 清空已有的字典
        self.srv_info_dict = {}
        for srv_idx in range(max_srv_id):
            self.request_ping(srv_idx)
            for ti in range(20):
                # 查询一个舵机最多等待1000ms
                self.update()
                if srv_idx in self.srv_info_dict:
                    break
                # 每隔100ms查询一次
                utime.sleep_ms(50)
            
    def request_query_srv_info(self, srv_id):
        '''查询单个舵机的所有配置'''
        self.send_request(self.CODE_QUERY_SERVO_INFO, struct.pack('<B', srv_id))
        # logging.info('查询单个舵机的所有配置 id={}'.format(srv_id))

    def request_set_srv_angle(self, srv_id, angle, interval=None, mean_dps=None, power=0):
        '''发送舵机角度控制请求
        @param srv_id 
            舵机的ID号
        @param angle 
            舵机的目标角度
        @param interval 
            中间间隔 单位ms
        @param mean_dps 
            平均转速 degree per second
        '''
        if srv_id not in self.srv_info_dict:
            logging.warn('未知舵机序号: {}'.format(srv_id))
            return False
        
        # 获取舵机信息
        srv_info = self.srv_info_dict[srv_id]
        
        if srv_info.cur_angle is None:
            # 初始状态还没有角度
            interval = 800
        elif interval is None and mean_dps is None:
            # 延时时间差不多是15ms旋转一度,可以比较平滑
            interval = int((abs(angle - srv_info.angle) / self.mean_dps) *1000)
        elif mean_dps is not None:
            # 根据mean_dps计算时间间隔 （转换为ms）
            interval = int((abs(angle - srv_info.angle) / mean_dps) *1000)
        
        # 同步修改srv_info
        self.srv_info_dict[srv_id].move(angle, interval)
        # 发送控制指令
        # 单位转换为0.1度
        angle = int(angle * 10)
        param_bytes = struct.pack('<BhHH', srv_id, angle, interval, power)
        self.send_request(self.CODE_SET_SERVO_ANGLE, param_bytes)
        
        return True

    def request_set_spin(self, srv_id, mode, value=0, is_cw=True, speed=None):
        '''设置舵机轮式模式控制
        @param srv_id
            舵机的ID号
        @param mode
            舵机的模式 取值范围[0,3]
        @param value 
            定时模式下代表时间(单位ms)
            定圈模式下代表圈数(单位圈)
        ＠param is_cw
            轮子的旋转方向, is_cw代表是否是顺指针旋转
        @param speed
            轮子旋转的角速度, 单位 度/s
        '''
        # 轮式模式的控制方法
        method = mode | 0x80 if is_cw else mode
        # 设置轮子旋转的角速度
        speed = self.mean_dps if speed is None else speed
        
        self.send_request(self.CODE_SET_SPIN, struct.pack('<BBHH', srv_id, method,speed, value))

    def request_set_damming(self, srv_id, power=0):
        '''设置阻尼模式
        @param srv_id
            舵机ID
        @param power
            舵机保持功率
        '''
        self.send_request(self.CODE_SET_DAMMING, struct.pack('<BH', srv_id, power))

    def update(self):
        '''舵机管理器的定时器回调函数'''
        # 清空原来的缓冲区
        self.pkt_buffer.empty_buffer()
        # 读入所有缓冲区的Bytes
        buffer_bytes = self.uart.readall()
        
        logging.info('Recv Bytes: ')
        logging.info(' '.join(['0x%02x'%b for b in buffer_bytes]))
        
        # 将读入的Bytes打包成数据帧
        if buffer_bytes is not None:
            for b in buffer_bytes:
                self.pkt_buffer.update( struct.pack('<B', b))
        # 相应回调数据
        while self.pkt_buffer.has_valid_packet():
            # 处理现有的返回数据帧
            response_bytes = self.pkt_buffer.get_packet()
            # 解包
            code, param_bytes = Packet.unpack(response_bytes)
            # 根据code找到相应处理函数
            if code in self.response_handle_funcs:
                self.response_handle_funcs[code](param_bytes)
            else:
                logging.warn('未知功能码 : {}'.format(code))
        # 更新舵机角度等状态信息
        for srv_id, srv_info in self.srv_info_dict.items():
            srv_info.update()
    
    def is_stop(self):
        '''判断所有的舵机是否均停止旋转'''
        for srv_id, srv_info in self.srv_info_dict.items():
            if not srv_info.is_stop():
                return False
        return True
