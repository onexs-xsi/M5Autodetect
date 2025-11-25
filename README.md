# M5Autodetect

[中文](#中文) | [日本語](#日本語) | [English](#english)

---

<a name="中文"></a>
## 中文

### 概述

M5Autodetect 是一个用于 M5Stack 产品的自动设备检测库。它可以通过检查 GPIO 引脚、I2C 设备、显示屏参数等硬件特征来自动识别连接的 M5Stack 设备型号。

### 功能特性

- 🔍 **自动检测** - 自动识别 M5Stack 设备
- 🖥️ **GUI 配置工具** - 可视化设备配置编辑器 (PyQt6)
- 📝 **YAML 配置** - 易于编辑的设备定义
- 🔧 **代码生成器** - 从 YAML 自动生成 C++ 头文件
- 🌐 **多语言支持** - 中文、英文、日文

### 项目结构

```
M5Autodetect/
├── src/                           # C++ 源文件
│   ├── M5Autodetect.cpp/.h        # 主检测类
│   ├── M5Autodetect_Bus.cpp/.h    # I2C/SPI 总线处理
│   └── M5Autodetect_Data.cpp/.h   # 生成的设备数据
├── M5Autodetect_GUI/              # Python GUI 工具
│   ├── M5Autodetect_CBuilder_GUI.py    # 主 GUI 应用
│   ├── M5Autodetect_CBuilder_GenCode.py # 代码生成器
│   ├── M5Flowchart_Demo.py        # 流程图可视化
│   ├── m5stack_dev_config.yaml    # 设备配置
│   ├── requirements.txt           # Python 依赖
│   └── locales/                   # 翻译文件
└── README.md
```

### Arduino/PlatformIO 使用

#### 基本用法

```cpp
#include <M5Autodetect.h>

M5Autodetect autodetect;

void setup() {
    Serial.begin(115200);
    
    // 启动检测（无调试输出）
    autodetect.begin();
    
    // 检测设备
    const m5::autodetect::DeviceInfo* info = autodetect.detect();
    
    if (info) {
        Serial.printf("检测到: %s\n", info->name);
        Serial.printf("SKU: %s\n", info->sku);
        Serial.printf("MCU: %s\n", info->mcu);
    } else {
        Serial.println("未检测到设备");
    }
}

void loop() {
    // 你的代码
}
```

#### 调试模式

```cpp
void setup() {
    Serial.begin(115200);
    
    // 启用调试输出
    autodetect.begin(M5Autodetect::debug_verbose, &Serial);
    
    // 带详细日志的检测
    autodetect.detect();
}
```

调试级别：
- `debug_none` - 无调试输出（默认）
- `debug_basic` - 基本检测结果
- `debug_verbose` - 详细的逐步日志

### 检测流程

检测按以下步骤进行：

1. **SOC 检查** - 匹配芯片型号（ESP32-S3、ESP32 等）
2. **IOMAP 检查** - 验证 GPIO 引脚状态
3. **I2C 引脚检查** - 确保 I2C 线路为高电平
4. **I2C 通信** - 检测 I2C 设备
5. **屏幕参数** - 通过 SPI 读取显示屏 ID
6. **额外测试** - 自定义 GPIO/I2C/SPI 测试

---

### Python GUI 工具

#### 系统要求

- Python 3.14 或更高版本
- PyQt6
- PyYAML
- requests
- pyqtgraph（用于流程图演示）
- numpy

#### 安装

```bash
# 进入 GUI 目录
cd lib/M5Autodetect/M5Autodetect_GUI

# 安装依赖
pip install -r requirements.txt
```

或手动安装：

```bash
pip install PyQt6>=6.6.0 PyYAML>=6.0.1 requests>=2.31.0 pyqtgraph>=0.13.3 numpy>=1.26.0
```

#### 运行 GUI 工具

**方法 1：直接 Python 执行**

```bash
# Windows PowerShell
cd lib\M5Autodetect\M5Autodetect_GUI
python M5Autodetect_CBuilder_GUI.py
```

**方法 2：明确指定 Python 3.14**

```bash
# Windows - 指定 Python 3.14 路径
& "C:/Program Files/Python314/python.exe" M5Autodetect_CBuilder_GUI.py

# 或者如果 Python 3.14 在 PATH 中
py -3.14 M5Autodetect_CBuilder_GUI.py
```

**方法 3：运行流程图演示**

```bash
python M5Flowchart_Demo.py
```

#### GUI 功能

1. **设备仪表板** - 所有配置设备的可视化网格
2. **树形导航** - MCU → 设备 → 引脚的层级视图
3. **设备编辑器** - 编辑设备属性：
   - 基本信息（名称、SKU、描述）
   - 检测引脚配置
   - I2C 总线和设备设置
   - 显示屏配置
   - 触摸配置
   - 变体支持
4. **YAML 编辑器** - 直接编辑 YAML
5. **代码生成器** - 生成 `M5Autodetect_Data.h/.cpp`

#### 生成头文件

1. 打开 GUI 工具
2. 根据需要编辑设备配置
3. 点击 **"💾 写入 YAML"** 保存更改
4. 点击 **"⚙️ 生成头文件 (.h)"** 生成 C++ 文件

或使用命令行：

```bash
python M5Autodetect_CBuilder_GenCode.py [yaml路径] [输出路径]

# 示例
python M5Autodetect_CBuilder_GenCode.py m5stack_dev_config.yaml ../src/M5Autodetect_Data.h
```

---

### 调试指南

#### Arduino/ESP32 调试

**1. 启用详细调试**

```cpp
autodetect.begin(M5Autodetect::debug_verbose, &Serial);
```

**2. 检查串口输出**

调试输出显示每个检测步骤：

```
=== Autodetect Start ===
Chip Model: ESP32-S3

-------------------
Checking: M5AtomS3R (SKU:C126)
  [Pass] SOC Match (+1)
  [Pass] IOMAP Match (+1) (2/2)
  [Pass] I2C Pins High (+1)
  [Pass] I2C Comm Match (+1) (2/2)
  [Pass] Screen ID Match (+1) (0x910EFF)
  [Skip] No Additional Tests (+1)
  Total Score: 6 (Skips: 1)

=== Detection Result ===
Best Match: M5AtomS3R (Score: 6, Skips: 1)
```

**3. 常见问题**

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| 未检测到设备 | 配置中 MCU 错误 | 检查 `mcu` 字段是否匹配芯片型号 |
| I2C 失败 | 无上拉电阻 | 启用 `internal_pullup: true` |
| 屏幕 ID 不匹配 | SPI 引脚错误 | 验证显示屏引脚配置 |
| 引脚检查失败 | GPIO 状态不正确 | 使用示波器验证 |

#### Python GUI 调试

**1. 检查 Python 版本**

```bash
python --version
# 应显示 Python 3.14.x
```

**2. 验证依赖**

```bash
pip list | findstr -i "pyqt6 pyyaml requests pyqtgraph numpy"
```

**3. 带调试输出运行**

GUI 会将调试信息打印到控制台：

```bash
python M5Autodetect_CBuilder_GUI.py
# 观察控制台中的 "Starting script..." 和任何错误
```

**4. 常见 Python 问题**

| 问题 | 解决方案 |
|------|----------|
| `ModuleNotFoundError: PyQt6` | 运行 `pip install PyQt6` |
| `qt.qpa.plugin: Could not load...` | 安装 Qt 平台插件或设置 `QT_QPA_PLATFORM_PLUGIN_PATH` |
| YAML 解析错误 | 检查配置文件中的 YAML 语法 |
| 图片下载失败 | 检查网络连接 |

**5. PyQt6 平台插件错误 (Windows)**

如果看到平台插件错误：

```powershell
# 设置环境变量
$env:QT_QPA_PLATFORM_PLUGIN_PATH = "C:\Path\To\Python314\Lib\site-packages\PyQt6\Qt6\plugins\platforms"

# 或重新安装 PyQt6
pip uninstall PyQt6 PyQt6-Qt6 PyQt6-sip
pip install PyQt6
```

---

### 添加新设备

**1. 编辑 YAML 配置**

在 `m5stack_dev_config.yaml` 中添加新设备条目：

```yaml
mcu_categories:
- mcu: ESP32-S3
  devices:
  - name: MyNewDevice
    description: 我的新 M5Stack 设备
    sku: SKU:XXXX
    eol: SALE
    image: https://example.com/image.webp
    docs: https://docs.m5stack.com/xxx
    
    check_pins:
      38:
        mode: input
        expect: 1
      39:
        mode: input_pullup
        expect: 0
    
    i2c_internal:
    - port: 0
      sda: 38
      scl: 39
      freq: 400000
      detect:
      - name: SensorName
        addr: 0x68  # 十六进制或十进制
    
    display:
    - driver: st7789
      width: 240
      height: 320
      freq: 40000000
      pins:
        mosi: 35
        sclk: 36
        cs: 37
        dc: 34
        rst: 33
        bl: 38
      identify:
        cmd: 0x04
        expect: 0x858552
        mask: 0xFFFFFF
        rst_before: true
        rst_wait: 120
    
    touch: []
    variants: []
```

**2. 生成头文件**

```bash
python M5Autodetect_CBuilder_GenCode.py
```

**3. 测试检测**

上传到您的设备并检查调试输出。

---

<a name="日本語"></a>
## 日本語

### 概要

M5Autodetect は M5Stack 製品用の自動デバイス検出ライブラリです。GPIO ピン、I2C デバイス、ディスプレイパラメータなどのハードウェア特性をチェックすることで、接続された M5Stack デバイスモデルを自動的に識別できます。

### 機能

- 🔍 **自動検出** - M5Stack デバイスを自動識別
- 🖥️ **GUI 設定ツール** - ビジュアルデバイス設定エディタ (PyQt6)
- 📝 **YAML 設定** - 編集しやすいデバイス定義
- 🔧 **コード生成** - YAML から C++ ヘッダーファイルを自動生成
- 🌐 **多言語対応** - 中国語、英語、日本語

### プロジェクト構成

```
M5Autodetect/
├── src/                           # C++ ソースファイル
│   ├── M5Autodetect.cpp/.h        # メイン検出クラス
│   ├── M5Autodetect_Bus.cpp/.h    # I2C/SPI バス処理
│   └── M5Autodetect_Data.cpp/.h   # 生成されたデバイスデータ
├── M5Autodetect_GUI/              # Python GUI ツール
│   ├── M5Autodetect_CBuilder_GUI.py    # メイン GUI アプリ
│   ├── M5Autodetect_CBuilder_GenCode.py # コード生成器
│   ├── M5Flowchart_Demo.py        # フローチャート可視化
│   ├── m5stack_dev_config.yaml    # デバイス設定
│   ├── requirements.txt           # Python 依存関係
│   └── locales/                   # 翻訳ファイル
└── README.md
```

### Arduino/PlatformIO の使用方法

#### 基本的な使い方

```cpp
#include <M5Autodetect.h>

M5Autodetect autodetect;

void setup() {
    Serial.begin(115200);
    
    // 検出開始（デバッグ出力なし）
    autodetect.begin();
    
    // デバイス検出
    const m5::autodetect::DeviceInfo* info = autodetect.detect();
    
    if (info) {
        Serial.printf("検出: %s\n", info->name);
        Serial.printf("SKU: %s\n", info->sku);
        Serial.printf("MCU: %s\n", info->mcu);
    } else {
        Serial.println("デバイスが検出されませんでした");
    }
}

void loop() {
    // あなたのコード
}
```

#### デバッグモード

```cpp
void setup() {
    Serial.begin(115200);
    
    // デバッグ出力を有効化
    autodetect.begin(M5Autodetect::debug_verbose, &Serial);
    
    // 詳細ログ付きで検出
    autodetect.detect();
}
```

デバッグレベル：
- `debug_none` - デバッグ出力なし（デフォルト）
- `debug_basic` - 基本的な検出結果
- `debug_verbose` - 詳細なステップバイステップログ

### 検出プロセス

検出は以下の手順で行われます：

1. **SOC チェック** - チップモデルの照合（ESP32-S3、ESP32 など）
2. **IOMAP チェック** - GPIO ピン状態の検証
3. **I2C ピンチェック** - I2C ラインが HIGH であることを確認
4. **I2C 通信** - I2C デバイスの検出
5. **スクリーンパラメータ** - SPI 経由でディスプレイ ID を読み取り
6. **追加テスト** - カスタム GPIO/I2C/SPI テスト

---

### Python GUI ツール

#### システム要件

- Python 3.14 以上
- PyQt6
- PyYAML
- requests
- pyqtgraph（フローチャートデモ用）
- numpy

#### インストール

```bash
# GUI ディレクトリに移動
cd lib/M5Autodetect/M5Autodetect_GUI

# 依存関係をインストール
pip install -r requirements.txt
```

または手動でインストール：

```bash
pip install PyQt6>=6.6.0 PyYAML>=6.0.1 requests>=2.31.0 pyqtgraph>=0.13.3 numpy>=1.26.0
```

#### GUI ツールの実行

**方法 1：Python 直接実行**

```bash
# Windows PowerShell
cd lib\M5Autodetect\M5Autodetect_GUI
python M5Autodetect_CBuilder_GUI.py
```

**方法 2：Python 3.14 を明示的に指定**

```bash
# Windows - Python 3.14 パスを指定
& "C:/Program Files/Python314/python.exe" M5Autodetect_CBuilder_GUI.py

# または Python 3.14 が PATH にある場合
py -3.14 M5Autodetect_CBuilder_GUI.py
```

**方法 3：フローチャートデモを実行**

```bash
python M5Flowchart_Demo.py
```

#### GUI 機能

1. **デバイスダッシュボード** - 設定済みデバイスのビジュアルグリッド
2. **ツリーナビゲーション** - MCU → デバイス → ピンの階層ビュー
3. **デバイスエディタ** - デバイスプロパティの編集：
   - 基本情報（名前、SKU、説明）
   - チェックピン設定
   - I2C バスとデバイス設定
   - ディスプレイ設定
   - タッチ設定
   - バリアント対応
4. **YAML エディタ** - YAML の直接編集
5. **コード生成** - `M5Autodetect_Data.h/.cpp` を生成

#### ヘッダーファイルの生成

1. GUI ツールを開く
2. 必要に応じてデバイス設定を編集
3. **"💾 写入 YAML"** をクリックして変更を保存
4. **"⚙️ 生成头文件 (.h)"** をクリックして C++ ファイルを生成

またはコマンドラインで：

```bash
python M5Autodetect_CBuilder_GenCode.py [yaml_path] [output_path]

# 例
python M5Autodetect_CBuilder_GenCode.py m5stack_dev_config.yaml ../src/M5Autodetect_Data.h
```

---

### デバッグガイド

#### Arduino/ESP32 デバッグ

**1. 詳細デバッグを有効化**

```cpp
autodetect.begin(M5Autodetect::debug_verbose, &Serial);
```

**2. シリアル出力を確認**

デバッグ出力は各検出ステップを表示します：

```
=== Autodetect Start ===
Chip Model: ESP32-S3

-------------------
Checking: M5AtomS3R (SKU:C126)
  [Pass] SOC Match (+1)
  [Pass] IOMAP Match (+1) (2/2)
  [Pass] I2C Pins High (+1)
  [Pass] I2C Comm Match (+1) (2/2)
  [Pass] Screen ID Match (+1) (0x910EFF)
  [Skip] No Additional Tests (+1)
  Total Score: 6 (Skips: 1)

=== Detection Result ===
Best Match: M5AtomS3R (Score: 6, Skips: 1)
```

**3. よくある問題**

| 問題 | 考えられる原因 | 解決策 |
|------|----------------|--------|
| デバイスが検出されない | 設定の MCU が間違っている | `mcu` フィールドがチップモデルと一致しているか確認 |
| I2C 失敗 | プルアップ抵抗がない | `internal_pullup: true` を有効化 |
| スクリーン ID 不一致 | SPI ピンが間違っている | ディスプレイピン設定を確認 |
| ピンチェック失敗 | GPIO 状態が正しくない | オシロスコープで確認 |

#### Python GUI デバッグ

**1. Python バージョンを確認**

```bash
python --version
# Python 3.14.x と表示されるはずです
```

**2. 依存関係を確認**

```bash
pip list | findstr -i "pyqt6 pyyaml requests pyqtgraph numpy"
```

**3. デバッグ出力付きで実行**

GUI はコンソールにデバッグ情報を出力します：

```bash
python M5Autodetect_CBuilder_GUI.py
# コンソールで "Starting script..." とエラーを確認
```

**4. よくある Python の問題**

| 問題 | 解決策 |
|------|--------|
| `ModuleNotFoundError: PyQt6` | `pip install PyQt6` を実行 |
| `qt.qpa.plugin: Could not load...` | Qt プラットフォームプラグインをインストールまたは `QT_QPA_PLATFORM_PLUGIN_PATH` を設定 |
| YAML 解析エラー | 設定ファイルの YAML 構文を確認 |
| 画像ダウンロード失敗 | ネットワーク接続を確認 |

**5. PyQt6 プラットフォームプラグインエラー (Windows)**

プラットフォームプラグインエラーが表示される場合：

```powershell
# 環境変数を設定
$env:QT_QPA_PLATFORM_PLUGIN_PATH = "C:\Path\To\Python314\Lib\site-packages\PyQt6\Qt6\plugins\platforms"

# または PyQt6 を再インストール
pip uninstall PyQt6 PyQt6-Qt6 PyQt6-sip
pip install PyQt6
```

---

### 新しいデバイスの追加

**1. YAML 設定を編集**

`m5stack_dev_config.yaml` に新しいデバイスエントリを追加：

```yaml
mcu_categories:
- mcu: ESP32-S3
  devices:
  - name: MyNewDevice
    description: 私の新しい M5Stack デバイス
    sku: SKU:XXXX
    eol: SALE
    image: https://example.com/image.webp
    docs: https://docs.m5stack.com/xxx
    
    check_pins:
      38:
        mode: input
        expect: 1
      39:
        mode: input_pullup
        expect: 0
    
    i2c_internal:
    - port: 0
      sda: 38
      scl: 39
      freq: 400000
      detect:
      - name: SensorName
        addr: 0x68  # 16 進数または 10 進数
    
    display:
    - driver: st7789
      width: 240
      height: 320
      freq: 40000000
      pins:
        mosi: 35
        sclk: 36
        cs: 37
        dc: 34
        rst: 33
        bl: 38
      identify:
        cmd: 0x04
        expect: 0x858552
        mask: 0xFFFFFF
        rst_before: true
        rst_wait: 120
    
    touch: []
    variants: []
```

**2. ヘッダーファイルを生成**

```bash
python M5Autodetect_CBuilder_GenCode.py
```

**3. 検出をテスト**

デバイスにアップロードしてデバッグ出力を確認。

---

<a name="english"></a>
## English

### Overview

M5Autodetect is an automatic device detection library for M5Stack products. It can automatically identify the connected M5Stack device model by checking GPIO pins, I2C devices, display parameters, and other hardware characteristics.

### Features

- 🔍 **Auto Detection** - Automatically identify M5Stack devices
- 🖥️ **GUI Configuration Tool** - Visual device configuration editor (PyQt6)
- 📝 **YAML Configuration** - Easy-to-edit device definitions
- 🔧 **Code Generator** - Auto-generate C++ header files from YAML
- 🌐 **Multi-language Support** - Chinese, English, Japanese

### Project Structure

```
M5Autodetect/
├── src/                           # C++ Source files
│   ├── M5Autodetect.cpp/.h        # Main autodetect class
│   ├── M5Autodetect_Bus.cpp/.h    # I2C/SPI bus handling
│   └── M5Autodetect_Data.cpp/.h   # Generated device data
├── M5Autodetect_GUI/              # Python GUI Tools
│   ├── M5Autodetect_CBuilder_GUI.py    # Main GUI application
│   ├── M5Autodetect_CBuilder_GenCode.py # Code generator
│   ├── M5Flowchart_Demo.py        # Flowchart visualization
│   ├── m5stack_dev_config.yaml    # Device configuration
│   ├── requirements.txt           # Python dependencies
│   └── locales/                   # Translation files
└── README.md
```

### Arduino/PlatformIO Usage

#### Basic Usage

```cpp
#include <M5Autodetect.h>

M5Autodetect autodetect;

void setup() {
    Serial.begin(115200);
    
    // Start detection (no debug output)
    autodetect.begin();
    
    // Detect device
    const m5::autodetect::DeviceInfo* info = autodetect.detect();
    
    if (info) {
        Serial.printf("Detected: %s\n", info->name);
        Serial.printf("SKU: %s\n", info->sku);
        Serial.printf("MCU: %s\n", info->mcu);
    } else {
        Serial.println("No device detected");
    }
}

void loop() {
    // Your code here
}
```

#### Debug Mode

```cpp
void setup() {
    Serial.begin(115200);
    
    // Enable debug output
    autodetect.begin(M5Autodetect::debug_verbose, &Serial);
    
    // Detect with detailed logging
    autodetect.detect();
}
```

Debug levels:
- `debug_none` - No debug output (default)
- `debug_basic` - Basic detection results
- `debug_verbose` - Detailed step-by-step logging

### Detection Process

The detection follows these steps:

1. **SOC Check** - Match chip model (ESP32-S3, ESP32, etc.)
2. **IOMAP Check** - Verify GPIO pin states
3. **I2C Pins Check** - Ensure I2C lines are HIGH
4. **I2C Communication** - Detect I2C devices
5. **Screen Parameters** - Read display ID via SPI
6. **Additional Tests** - Custom GPIO/I2C/SPI tests

---

### Python GUI Tool

#### Requirements

- Python 3.14 or higher
- PyQt6
- PyYAML
- requests
- pyqtgraph (for flowchart demo)
- numpy

#### Installation

```bash
# Navigate to the GUI directory
cd lib/M5Autodetect/M5Autodetect_GUI

# Install dependencies
pip install -r requirements.txt
```

Or install manually:

```bash
pip install PyQt6>=6.6.0 PyYAML>=6.0.1 requests>=2.31.0 pyqtgraph>=0.13.3 numpy>=1.26.0
```

#### Running the GUI Tool

**Method 1: Direct Python Execution**

```bash
# Windows PowerShell
cd lib\M5Autodetect\M5Autodetect_GUI
python M5Autodetect_CBuilder_GUI.py
```

**Method 2: With Python 3.14 Explicitly**

```bash
# Windows - specify Python 3.14 path
& "C:/Program Files/Python314/python.exe" M5Autodetect_CBuilder_GUI.py

# Or if Python 3.14 is in PATH
py -3.14 M5Autodetect_CBuilder_GUI.py
```

**Method 3: Run Flowchart Demo**

```bash
python M5Flowchart_Demo.py
```

#### GUI Features

1. **Device Dashboard** - Visual grid of all configured devices
2. **Tree Navigation** - Hierarchical view of MCU → Device → Pins
3. **Device Editor** - Edit device properties:
   - Basic info (name, SKU, description)
   - Check pins configuration
   - I2C bus and device settings
   - Display configuration
   - Touch configuration
   - Variants support
4. **YAML Editor** - Direct YAML editing
5. **Code Generator** - Generate `M5Autodetect_Data.h/.cpp`

#### Generating Header Files

1. Open the GUI tool
2. Edit device configurations as needed
3. Click **"💾 写入 YAML"** to save changes
4. Click **"⚙️ 生成头文件 (.h)"** to generate C++ files

Or use command line:

```bash
python M5Autodetect_CBuilder_GenCode.py [yaml_path] [output_path]

# Example
python M5Autodetect_CBuilder_GenCode.py m5stack_dev_config.yaml ../src/M5Autodetect_Data.h
```

---

### Debugging Guide

#### Arduino/ESP32 Debugging

**1. Enable Verbose Debug**

```cpp
autodetect.begin(M5Autodetect::debug_verbose, &Serial);
```

**2. Check Serial Output**

The debug output shows each detection step:

```
=== Autodetect Start ===
Chip Model: ESP32-S3

-------------------
Checking: M5AtomS3R (SKU:C126)
  [Pass] SOC Match (+1)
  [Pass] IOMAP Match (+1) (2/2)
  [Pass] I2C Pins High (+1)
  [Pass] I2C Comm Match (+1) (2/2)
  [Pass] Screen ID Match (+1) (0x910EFF)
  [Skip] No Additional Tests (+1)
  Total Score: 6 (Skips: 1)

=== Detection Result ===
Best Match: M5AtomS3R (Score: 6, Skips: 1)
```

**3. Common Issues**

| Issue | Possible Cause | Solution |
|-------|----------------|----------|
| No device detected | Wrong MCU in config | Check `mcu` field matches chip model |
| I2C Fail | No pullup resistors | Enable `internal_pullup: true` |
| Screen ID Mismatch | Wrong SPI pins | Verify display pin configuration |
| Pin check fail | Incorrect GPIO state | Use oscilloscope to verify |

#### Python GUI Debugging

**1. Check Python Version**

```bash
python --version
# Should show Python 3.14.x
```

**2. Verify Dependencies**

```bash
pip list | findstr -i "pyqt6 pyyaml requests pyqtgraph numpy"
```

**3. Run with Debug Output**

The GUI prints debug info to console:

```bash
python M5Autodetect_CBuilder_GUI.py
# Watch console for "Starting script..." and any errors
```

**4. Common Python Issues**

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: PyQt6` | Run `pip install PyQt6` |
| `qt.qpa.plugin: Could not load...` | Install Qt platform plugins or set `QT_QPA_PLATFORM_PLUGIN_PATH` |
| YAML parsing error | Check YAML syntax in config file |
| Image download failed | Check network connection |

**5. PyQt6 Platform Plugin Error (Windows)**

If you see platform plugin errors:

```powershell
# Set environment variable
$env:QT_QPA_PLATFORM_PLUGIN_PATH = "C:\Path\To\Python314\Lib\site-packages\PyQt6\Qt6\plugins\platforms"

# Or reinstall PyQt6
pip uninstall PyQt6 PyQt6-Qt6 PyQt6-sip
pip install PyQt6
```

---

### Adding New Devices

**1. Edit YAML Configuration**

Add a new device entry in `m5stack_dev_config.yaml`:

```yaml
mcu_categories:
- mcu: ESP32-S3
  devices:
  - name: MyNewDevice
    description: My new M5Stack device
    sku: SKU:XXXX
    eol: SALE
    image: https://example.com/image.webp
    docs: https://docs.m5stack.com/xxx
    
    check_pins:
      38:
        mode: input
        expect: 1
      39:
        mode: input_pullup
        expect: 0
    
    i2c_internal:
    - port: 0
      sda: 38
      scl: 39
      freq: 400000
      detect:
      - name: SensorName
        addr: 0x68  # Hex or decimal
    
    display:
    - driver: st7789
      width: 240
      height: 320
      freq: 40000000
      pins:
        mosi: 35
        sclk: 36
        cs: 37
        dc: 34
        rst: 33
        bl: 38
      identify:
        cmd: 0x04
        expect: 0x858552
        mask: 0xFFFFFF
        rst_before: true
        rst_wait: 120
    
    touch: []
    variants: []
```

**2. Generate Header Files**

```bash
python M5Autodetect_CBuilder_GenCode.py
```

**3. Test Detection**

Upload to your device and check debug output.

---

## License

MIT License

## Author

M5Stack - support@m5stack.com
