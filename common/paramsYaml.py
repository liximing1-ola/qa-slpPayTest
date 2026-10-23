# coding=utf-8
import yaml
from common.Config import config
import os
import platform


class Yaml:
    @staticmethod
    def read_yaml(yaml_fileName, yaml_name):
        """
        读取yaml
        :return: yaml_data[yaml_name]
        """
        yaml_path = os.path.join(config.BASE_PATH, 'common', yaml_fileName)
        try:
            if not os.path.exists(yaml_path):
                return FileExistsError
            if platform.node() == config.linux_node['ali']:
                yaml_data = yaml.load(open(yaml_path, 'r', encoding='utf-8'), Loader=yaml.SafeLoader)  # 添加后不会报warning
            elif platform.node() == config.linux_node['ali-slp']:
                yaml_data = yaml.load(open(yaml_path, 'r', encoding='utf-8'), Loader=yaml.SafeLoader)  # 添加后不会报warning
            else:
                yaml_data = yaml.load(open(yaml_path, 'r', encoding='utf-8'))
            if yaml_data[yaml_name] is None:
                return TypeError
            else:
                return yaml_data[yaml_name]
        except Exception as error:
            print(error)
