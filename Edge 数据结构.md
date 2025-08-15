Edge 数据结构
 Redis 作为实时数据总线，提供毫秒级的跨服务数据交换；InfluxDB 作为时序数据仓库，持久化存储历史数据。各微服务通过独立键空间在 Redis 中进行实时同步，历史数据自动归档至 InfluxDB 进行长期分析。


数据流图
 
Redis 数据结构
1. Comsrv (通信服务)
1.1 实时数据存储
•	类型: Hash
•	格式: comsrv:{channel_id}:{type}
•	类型定义:
￮	T - Telemetry (遥测)
￮	S - Signal (遥信)
￮	C - Control (遥控)
￮	A - Adjustment (遥调)
Plain Text
# 遥测数据示例
comsrv:1001:T
  1 -> "25.5"      # 温度值
  2 -> "380.2"     # 电压值
  3 -> "12.8"      # 电流值

# 遥信数据示例
comsrv:1001:S
  1 -> "1"         # 开关状态 (0/1)
  2 -> "0"         # 告警状态

# 遥控数据示例  
comsrv:1001:C
  100 -> "1"       # 启停控制
  101 -> "0"       # 复位控制

# 遥调数据示例
comsrv:1001:A
  200 -> "75.5"    # 设定值
  201 -> "100.0"   # 阈值
1.2 命令触发队列
•	类型: List
•	格式: comsrv:trigger:{channel_id}:{type}
•	用途: 异步命令执行队列（BLPOP消费）
JSON
{
  "point_id": 100,
  "value": 1,
  "source": "",（Optional）
  "command_id": "cmd_1234567890",(Optional)
  "timestamp": 1754530782(Optional)
}
2. Modsrv (模型服务)
2.1 模型定义
•	类型: String (JSON)
•	格式: modsrv:model:{model_id}
JSON
{
  "id": "model_001",
  "name": "变压器模型",
  "template": "transformer",
  "properties": {
    "rated_power": 1000,
    "voltage_level": "10kV"
  },
  "mappings": {
    "measurement": {
      "temperature": {"channel": 1001, "point_id": 1, "type": "T"},
      "voltage_a": {"channel": 1001, "point_id": 2, "type": "T"},
      "current_a": {"channel": 1001, "point_id": 3, "type": "T"}
    },
    "action": {
      "start_stop": {"channel": 1001, "point_id": 100, "type": "C"},
      "setpoint": {"channel": 1001, "point_id": 200, "type": "A"}
    }
  }
}
2.2 模型实时值
•	类型: Hash
•	格式: modsrv:model:{model_id}:measurement（测量值）
•	格式: modsrv:model:{model_id}:action（控制值）
Plain Text
modsrv:model:model_001:measurement
  temperature -> "25.5"
  voltage_a -> "380.2"
  current_a -> "12.8"
  __updated -> "1754530782"  # 更新时间戳

modsrv:model:model_001:action
  start_stop -> "1"
  setpoint -> "75.5"
2.3 反向映射索引
•	类型: String
•	格式: modsrv:reverse:{channel_id}:{point_id}（测量点）
•	格式: modsrv:reverse:action:{channel_id}:{point_id}（控制点）
•	值: {model_id}:{point_name}
Plain Text
modsrv:reverse:1001:1 -> "model_001:temperature"
modsrv:reverse:1001:2 -> "model_001:voltage_a"
modsrv:reverse:action:1001:100 -> "model_001:start_stop"
2.4 模板索引
•	类型: Set
•	格式: modsrv:models:by_template:{template_name}
Plain Text
modsrv:models:by_template:transformer -> ["model_001", "model_002"]
3. Alarmsrv (告警服务)
3.1 告警记录
•	类型: Hash
•	格式: alarmsrv:{alarm_id}
Plain Text
alarmsrv:alarm_12345
  id -> "alarm_12345"
  title -> "温度过高"
  description -> "变压器温度超过85度"
  level -> "Critical"
  status -> "Active"
  source -> "modsrv:model:{model_id}"
  timestamp -> "1754530782"
  acknowledged -> "false"（Optional）
  acknowledged_by -> ""（Optional）
  acknowledged_at -> "（Optional）
3.2 告警索引
•	类型: Set
•	格式: 
￮	alarmsrv:index - 所有告警
￮	alarmsrv:status:{status} - 按状态分组
￮	alarmsrv:level:{level} - 按级别分组
￮	alarmsrv:source:{source} - 按来源分组
Plain Text
alarmsrv:index -> ["alarm_12345", "alarm_12346"]
alarmsrv:status:Active -> ["alarm_12345"]
alarmsrv:level:Critical -> ["alarm_12345"]
alarmsrv:source:comsrv:1001:T:1 -> ["alarm_12345"]
4. Rulesrv (规则服务)
4.1 规则定义
•	类型: String (JSON)
•	格式: rulesrv:rule:{rule_id}
JSON
{
  "id": "rule_001",
  "name": "温度保护",
  "enabled": true,
  "condition": "comsrv:1001:T:1 > 85",
  "actions": [
    {
      "type": "alarm",
      "params": {
        "level": "Critical",
        "title": "温度过高"
      }
    },
    {
      "type": "control",
      "target": "comsrv:1001:C:100",
      "value": 0
    }
  ],
  "cooldown": 300
}
4.2 规则元数据
•	类型: Hash
•	格式: rulesrv:rule:{rule_id}:meta
Plain Text
rulesrv:rule:rule_001:meta
  execution_count -> "10"
  last_executed -> "1754530782"
  last_result -> "triggered"
  created_at -> "1754530000"
  updated_at -> "1754530100"
4.3 规则状态
•	类型: Hash
•	格式: rulesrv:rule:{rule_id}:state
Plain Text
rulesrv:rule:rule_001:state
  last_value -> "87.5"
  last_triggered -> "1754530782"
  trigger_count -> "3"
  condition_met -> "true"
4.4 规则索引
•	类型: Set
•	格式:
￮	rulesrv:rules - 所有规则
￮	rulesrv:rules:active - 激活的规则
5. Hissrv (历史服务)
5.1 历史数据缓冲
•	类型: List
•	格式: hissrv:buffer:{source_key}
•	说明: 临时缓冲，定期写入InfluxDB
JSON
// List中的数据格式
{
  "timestamp": 1754530782,
  "point_id": 1,
  "value": 25.5,
}
6. Sync Engine (同步引擎)
6.1 同步规则配置
•	类型: String (JSON)
•	格式: sync:config:{rule_id}
JSON
{
  "source": {
    "pattern": "comsrv:*:T",
    "type": "hash",
    "fields": ["1", "2", "3"]
  },
  "target": {
    "pattern": "modsrv:model:1:measurement",
    "type": "hash"
  },
  "field_mapping": {
    "1": "temperature",
    "2": "voltage",
    "3": "current"
  },
  "transform": {
    "type": "numeric",
    "scale": 1.0,
    "offset": 0
  },
  "reverse_mapping": {
    "enabled": true
  },
  "enabled": true
}
6.2 同步统计
•	类型: Hash
•	格式: sync:stats:{rule_id}
Plain Text
sync:stats:rule_001
  sync_count -> "1000"
  last_sync -> "1754530782"
  error_count -> "0"
  last_error -> ""
6.3 反向映射
•	类型: String
•	格式: sync:reverse:{rule_id}:{source_key}:{field}
•	值: {target_key}:{target_field}

服务间数据流
1. 采集数据流
Plain Text
设备 → Comsrv (协议转换) → Redis Hash → Sync Engine → Modsrv/Hissrv/Alarmsrv
2. 控制命令流
Plain Text
API/Modsrv → Redis Hash + List Queue → CommandTrigger → 协议处理 → 设备
3. 同步流程
Plain Text
源数据变更 → Sync Engine检测 → 转换处理 → 目标数据更新 → [触发命令队列]

命令与控制流程
1. 控制命令执行流程
1.1 API触发
Plain Text
POST /api/control/{channel_id}
  ↓
写入 comsrv:{channel_id}:C (Hash)
  ↓
推送到 comsrv:trigger:{channel_id}:C (List)
  ↓
CommandTrigger BLPOP获取
  ↓
协议处理器执行
  ↓
设备响应
1.2 同步引擎触发
Plain Text
Modsrv数据变更
  ↓
Sync Engine检测到控制点映射
  ↓
写入 comsrv:{channel_id}:C (Hash)
  ↓
推送到 comsrv:trigger:{channel_id}:C (List)
  ↓
CommandTrigger处理（同上）
2. 命令数据格式
2.1 List队列命令格式
JSON
{
  "point_id": 100,        // 点位ID
  "value": 1,             // 控制值
  "source": "api",        // 来源: api/sync_engine/manual
  "command_id": "cmd_123", // 命令ID（用于追踪）
  "timestamp": 1754530782 // Unix时间戳
}
3. 命令超时处理
•	List队列设置30秒过期时间
•	BLPOP超时后重新监听
•	失败命令可重试或记录

数据精度与格式
1. 数值精度
•	所有浮点数保留6位小数
•	时间戳使用Unix时间（秒）
•	毫秒级时间戳用于命令ID生成
2. 布尔值表示
•	Redis中: "0" / "1" 字符串
•	CSV中: false / true
•	Modbus: 0x0000 / 0xFF00
3. 字节序支持
•	16位: AB, BA
•	32位: ABCD, DCBA, BADC, CDAB
•	64位: ABCDEFGH及各种组合

最佳实践
1. 命名规范
•	Channel ID: 1-9999
•	Point ID: 从1开始连续编号
•	Model ID: 有意义的英文标识符
•	Rule ID: 功能_序号格式
2. 性能优化
•	使用Hash批量操作
•	BLPOP实现零CPU等待
•	合理设置同步频率
•	及时清理过期数据
3. 数据安全
•	命令队列设置过期时间
•	重要操作记录日志
•	反向映射用于数据追溯
•	定期备份配置数据

附录：Redis操作示例
查看实时数据
Bash
# 查看所有遥测点
redis-cli hgetall "comsrv:1001:T"

# 查看特定点位
redis-cli hget "comsrv:1001:T" "1"

# 查看队列长度
redis-cli llen "comsrv:trigger:1001:C"

# 查看队列内容（不移除）
redis-cli lrange "comsrv:trigger:1001:C" 0 -1
手动触发命令
Bash
# 推送控制命令
redis-cli rpush "comsrv:trigger:1001:C" '{"point_id":100,"value":1,"source":"manual","command_id":"manual_001","timestamp":1754530782}'

# 设置控制值
redis-cli hset "comsrv:1001:C" "100" "1"
同步操作
Bash
# 执行同步
redis-cli fcall sync_execute 3 "rule_001" "comsrv:1001:T" "modsrv:model:001:measurement"

# 查看同步统计
redis-cli hgetall "sync:stats:rule_001"

