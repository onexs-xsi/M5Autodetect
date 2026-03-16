# Plan: I2C 设备必须/可选存在标记功能

## 背景

`i2c_internal` 下的 `detect` 列表当前只用一个全局计数阈值 (`detect_count`) 判断 I2C 总线检测是否通过，无法区分"某设备必须存在"与"某设备可选存在"。

## 需求

为 `detect` 列表中的每个 I2C 设备条目增加 `required` 字段：
- `required: true`（默认）：该设备必须 ACK，否则此总线检测直接失败。
- `required: false`：该设备可选，不存在不影响通过判断。

## 涉及文件

| 文件 | 修改摘要 |
|------|---------|
| `src/data/M5Autodetect_DeviceData.h` | `I2CDetect` 结构体新增 `bool required` 字段 |
| `M5Autodetect_GUI/M5Autodetect_CBuilder_GenCode.py` | 生成 `I2CDetect` 结构声明时加入 `bool required`；生成数据初始化时输出 `required` 值；`detect_count` 默认值改为 必须设备数量 |
| `src/M5Autodetect.cpp` | I2C 检测循环：`required=true` 设备未找到 → 硬失败；`required=false` 设备未找到 → 继续，仅记录 Info 日志 |
| `M5Autodetect_GUI/M5Autodetect_CBuilder_GUI.py` | 检测设备表格增加第三列"必须"（QCheckBox）；`_add_detect_row` 读写 `required`；`_collect_data_from_ui` 收集 `required` 字段 |

## 设计细节

### YAML 格式（变化最小化）

```yaml
i2c_internal:
- port: 0
  sda: 38
  scl: 39
  freq: 400000
  detect:
  - name: BMI270
    addr: 104
    required: true       # 明确标注必须 (可省略，默认 true)
  - name: LP5562
    addr: 48
    required: false      # 可选设备
```

`required` 键仅在为 `false` 时写入 YAML（减少噪音，保持向后兼容）。

### C++ 逻辑（I2C 通信检测步骤）

```
对每条 i2c_bus：
  bus_found_count = 0
  bus_required_all_found = true
  对每个 detect 条目：
    ack = 尝试 beginTransmission/endTransmission
    if ack:
      bus_found_count++
    else if detect.required:
      bus_required_all_found = false   ← 硬失败标记
      LOG [Fail]
    else:
      LOG [Info] optional missing (ok)
  i2c_device_required_count += 本总线必须设备数
  if (!bus_required_all_found || bus_found_count < detect_count):
    i2c_comm_match = false; break
```

### `detect_count` 默认值变化（GenCode）

旧：`detect_count = len(detect)`（所有设备都必须找到）

新：`detect_count = sum(1 for d in detect if d.get('required', True))`

向后兼容：若所有设备均为默认 `required=true`，结果与之前相同。

## 实施步骤（已完成）

1. ✅ 写 plan.md
2. ✅ 修改 `DeviceData.h` — `I2CDetect` 增加 `bool required`
3. ✅ 修改 `GenCode.py` — 结构声明 + 数据生成 + `detect_count` 默认值
4. ✅ 修改 `M5Autodetect.cpp` — 检测循环加 required/optional 分支
5. ✅ 修改 `GUI.py` — 检测表格第三列 + `_collect_data_from_ui`
