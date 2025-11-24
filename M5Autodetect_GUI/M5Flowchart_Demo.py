import sys
import os
import yaml
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QMessageBox
import pyqtgraph as pg
from pyqtgraph.flowchart import Flowchart, Node
import pyqtgraph.flowchart.library as fclib

# 1. 定义自定义节点
# pyqtgraph 的节点通常用于处理数据，但我们这里主要用作数据容器和可视化

class BaseConfigNode(Node):
    """配置节点的基类"""
    def __init__(self, name, terminals=None, allowAddInput=False, allowAddOutput=False):
        super().__init__(name, terminals, allowAddInput, allowAddOutput)
        self.config_data = {}

    def set_config(self, data):
        self.config_data = data
        # 这里可以添加逻辑来更新节点的 CtrlWidget (属性面板)

class MCUNode(BaseConfigNode):
    nodeName = 'MCU'
    def __init__(self, name):
        terminals = {
            'devices': {'io': 'out'}
        }
        super().__init__(name, terminals=terminals)

class DeviceNode(BaseConfigNode):
    nodeName = 'Device'
    def __init__(self, name):
        terminals = {
            'in_mcu': {'io': 'in'},
            'pins': {'io': 'out'},
            'i2c': {'io': 'out'},
            'display': {'io': 'out'},
            'touch': {'io': 'out'}
        }
        super().__init__(name, terminals=terminals)

class PinCheckNode(BaseConfigNode):
    nodeName = 'PinCheck'
    def __init__(self, name):
        terminals = {
            'in_device': {'io': 'in'}
        }
        super().__init__(name, terminals=terminals)

class I2CBusNode(BaseConfigNode):
    nodeName = 'I2CBus'
    def __init__(self, name):
        terminals = {
            'in_device': {'io': 'in'},
            'detect': {'io': 'out'}
        }
        super().__init__(name, terminals=terminals)

class I2CDeviceNode(BaseConfigNode):
    nodeName = 'I2CDevice'
    def __init__(self, name):
        terminals = {
            'in_bus': {'io': 'in'}
        }
        super().__init__(name, terminals=terminals)

class DisplayNode(BaseConfigNode):
    nodeName = 'Display'
    def __init__(self, name):
        terminals = {
            'in_device': {'io': 'in'}
        }
        super().__init__(name, terminals=terminals)

class TouchNode(BaseConfigNode):
    nodeName = 'Touch'
    def __init__(self, name):
        terminals = {
            'in_device': {'io': 'in'}
        }
        super().__init__(name, terminals=terminals)

# 2. 注册节点库
# 我们创建一个新的库分类 'M5Stack'
library = fclib.LIBRARY.copy() 
library.addNodeType(MCUNode, [('M5Stack',)])
library.addNodeType(DeviceNode, [('M5Stack',)])
library.addNodeType(PinCheckNode, [('M5Stack',)])
library.addNodeType(I2CBusNode, [('M5Stack',)])
library.addNodeType(I2CDeviceNode, [('M5Stack',)])
library.addNodeType(DisplayNode, [('M5Stack',)])
library.addNodeType(TouchNode, [('M5Stack',)])

# 3. 主窗口
class FlowchartDemo(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("M5Stack Config Flowchart (pyqtgraph)")
        self.resize(1200, 800)

        cw = QWidget()
        self.setCentralWidget(cw)
        layout = QVBoxLayout()
        cw.setLayout(layout)

        # 创建 Flowchart
        # terminals 参数定义了整个流程图的输入输出，这里我们不需要全局输入输出，所以留空或给个默认
        self.fc = Flowchart(terminals={})
        self.fc.setLibrary(library)

        # 获取流程图的控件
        # pyqtgraph 的 flowchart.widget() 返回一个包含节点列表和属性面板的 Splitter
        # 我们主要需要显示 ChartGraphicsView (图表视图)
        
        # 1. Chart View (节点图)
        self.chart_widget = self.fc.widget().chartWidget
        layout.addWidget(self.chart_widget)
        
        # 2. Control Panel (属性面板 - 可选)
        # layout.addWidget(self.fc.widget().ctrlWidget)

        # 加载数据
        self.load_yaml()

    def load_yaml(self):
        yaml_path = os.path.join(os.path.dirname(__file__), 'm5stack_dev_config.yaml')
        if not os.path.exists(yaml_path):
            QMessageBox.warning(self, "Error", "YAML file not found")
            return
            
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load YAML: {e}")
            return
            
        # 编程式添加节点
        x_start = 0
        y_start = 0
        
        mcu_categories = data.get('mcu_categories', [])
        for cat in mcu_categories:
            mcu_name = cat.get('mcu', 'Unknown')
            # 创建 MCU 节点
            mcu_node = self.fc.createNode('MCU', name=mcu_name, pos=(x_start, y_start))
            mcu_node.set_config(cat)
            
            dev_x = x_start + 250
            dev_y = y_start
            
            for dev in cat.get('devices', []):
                dev_name = dev.get('name', 'Unknown')
                # 创建 Device 节点
                dev_node = self.fc.createNode('Device', name=dev_name, pos=(dev_x, dev_y))
                dev_node.set_config(dev)
                
                # 连接 MCU -> Device
                # 注意：pyqtgraph 允许一对多连接
                self.fc.connectTerminals(mcu_node['devices'], dev_node['in_mcu'])
                
                child_x = dev_x + 250
                child_y = dev_y
                
                # Pins
                check_pins = dev.get('check_pins', {})
                pins_list = []
                if isinstance(check_pins, dict):
                    for k, v in check_pins.items():
                        v['gpio'] = k
                        pins_list.append(v)
                elif isinstance(check_pins, list):
                    pins_list = check_pins
                
                for pin in pins_list:
                    pin_name = f"GPIO {pin.get('gpio')}"
                    pin_node = self.fc.createNode('PinCheck', name=pin_name, pos=(child_x, child_y))
                    pin_node.set_config(pin)
                    self.fc.connectTerminals(dev_node['pins'], pin_node['in_device'])
                    child_y += 100
                    
                # I2C
                i2c_internal = dev.get('i2c_internal', [])
                for i2c in i2c_internal:
                    bus_name = f"I2C Port {i2c.get('port')}"
                    bus_node = self.fc.createNode('I2CBus', name=bus_name, pos=(child_x, child_y))
                    bus_node.set_config(i2c)
                    self.fc.connectTerminals(dev_node['i2c'], bus_node['in_device'])
                    
                    # I2C Devices
                    detects = i2c.get('detect', [])
                    detect_x = child_x + 250
                    detect_y = child_y
                    for d in detects:
                        d_name = d.get('name', 'Unknown')
                        d_node = self.fc.createNode('I2CDevice', name=d_name, pos=(detect_x, detect_y))
                        d_node.set_config(d)
                        self.fc.connectTerminals(bus_node['detect'], d_node['in_bus'])
                        detect_y += 100
                    
                    child_y = max(child_y + 100, detect_y)

                # Display
                displays = dev.get('display', [])
                for disp in displays:
                    disp_name = f"Display {disp.get('driver')}"
                    disp_node = self.fc.createNode('Display', name=disp_name, pos=(child_x, child_y))
                    disp_node.set_config(disp)
                    self.fc.connectTerminals(dev_node['display'], disp_node['in_device'])
                    child_y += 100

                # Touch
                touches = dev.get('touch', [])
                for touch in touches:
                    touch_name = f"Touch {touch.get('driver')}"
                    touch_node = self.fc.createNode('Touch', name=touch_name, pos=(child_x, child_y))
                    touch_node.set_config(touch)
                    self.fc.connectTerminals(dev_node['touch'], touch_node['in_device'])
                    child_y += 100
                
                dev_y = max(dev_y + 150, child_y)
            
            y_start = dev_y + 100

if __name__ == '__main__':
    app = QApplication(sys.argv)
    # 设置 pyqtgraph 的配置
    pg.setConfigOption('background', 'w') # 白色背景
    pg.setConfigOption('foreground', 'k') # 黑色前景
    
    win = FlowchartDemo()
    win.show()
    sys.exit(app.exec())
