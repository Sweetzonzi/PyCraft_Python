import os
import math
import time
import sys


def _find_project_root():
    """从脚本位置向上查找项目根目录（包含 py_port/ Python 包的目录）"""
    current = os.path.dirname(os.path.abspath(__file__))
    while True:
        py_port_dir = os.path.join(current, "py_port")
        if os.path.isdir(py_port_dir) and os.path.isfile(os.path.join(py_port_dir, "__init__.py")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


_project_root = _find_project_root()
if _project_root and _project_root not in sys.path:
    sys.path.insert(0, _project_root)
del _project_root, _find_project_root


from py_port.turtle_controller import TurtleController

t = TurtleController(agent_id=1)
t.front(3)
t.right(90)
t.front(3)
t.right(90)
t.front(3)
t.right(90)
t.front(2)
t.right(90)
t.front(3)
t.right(45)
t.front(3)
t.right(45)

print("end")


