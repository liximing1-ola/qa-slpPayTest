import os
from common.Config import config

try:
    from markdown import markdown
except ModuleNotFoundError as e:
    os.system("pip3 install markdown")
    os.system("pip3 install python-markdown-math")
    os.system("pip3 install markdown_checklist")
    from markdown import markdown
try:
    from pymdownx import superfences
except ModuleNotFoundError as e:
    os.system("pip3 install pymdown-extensions")
    from pymdownx import superfences


# pip3 install xx -i http://mirrors.aliyun.com/pypi/simple --trusted-host mirrors.aliyun.com
# 如果不行换个源

class mdtox:
    def __init__(self, md_filename, encoding='utf-8'):
        self.html = None
        self.md_filename = md_filename
        self.encoding = encoding
        self.__args()

    def __args(self):
        self.html = '''
        <!DOCTYPE html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1, minimal-ui">
                <title>{}</title>
                <link rel="stylesheet" href="https://files.cnblogs.com/files/bpf-1024/linenum.css">
                <link rel="stylesheet" href="https://files.cnblogs.com/files/bpf-1024/markdown.css">
                <link rel="stylesheet" href="https://files.cnblogs.com/files/bpf-1024/tasklist.css">
                <link rel="stylesheet" href="https://files.cnblogs.com/files/bpf-1024/codehighlight.css">
                <link rel="stylesheet" href="https://files.cnblogs.com/files/bpf-1024/directory.css">
                <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex/dist/katex.min.css" crossorigin="anonymous">
                <script src="https://files.cnblogs.com/files/bpf-1024/directory.js"></script>
                <script src="https://unpkg.com/mermaid@8.7.0/dist/mermaid.min.js"></script>
                <script src="https://cdn.jsdelivr.net/npm/katex/dist/katex.min.js" crossorigin="anonymous"></script>
                <script src="https://cdn.jsdelivr.net/npm/katex/dist/contrib/mathtex-script-type.min.js" defer></script>
            </head>
            <body>
                <article class="markdown-body" id="markdown-body">
                    {}
                </article>
            </body>
        </html>
        '''

        # 扩展配置
        self.extensions = [
            'toc',  # 目录，[toc]
            'extra',  # 缩写词、属性列表、释义列表、围栏式代码块、脚注、在HTML的Markdown、表格
        ]
        third_party_extensions = [
            'mdx_math',  # KaTeX数学公式，$E=mc^2$和$$E=mc^2$$
            'markdown_checklist.extension',  # checklist，- [ ]和- [x]
            'pymdownx.magiclink',  # 自动转超链接，
            'pymdownx.caret',  # 上标下标，
            'pymdownx.superfences',  # 多种块功能允许嵌套，各种图表
            'pymdownx.betterem',  # 改善强调的处理(粗体和斜体)
            'pymdownx.mark',  # 亮色突出文本
            'pymdownx.highlight',  # 高亮显示代码
            'pymdownx.tasklist',  # 任务列表
            'pymdownx.tilde',  # 删除线
        ]
        self.extensions.extend(third_party_extensions)
        self.extension_configs = {
            'mdx_math': {
                'enable_dollar_delimiter': True  # 允许单个$
            },
            'pymdownx.superfences': {
                "custom_fences": [
                    {
                        'name': 'mermaid',  # 开启流程图等图
                        'class': 'mermaid',
                        'format': superfences.fence_div_format
                    }
                ]
            },
            'pymdownx.highlight': {
                'linenums': True,  # 显示行号
                'linenums_style': 'pymdownx-inline'  # 代码和行号分开
            },
            'pymdownx.tasklist': {
                'clickable_checkbox': True,  # 任务列表可点击
            }
        }

    def to_html(self, html_path):
        try:
            with open(self.md_filename, "r", encoding=self.encoding) as file_md:
                md_text = file_md.read()
        except Exception as error:
            print("<Error>", error)
            return False

        title = '.'.join(os.path.basename(self.md_filename).split('.')[:-1])
        html_text = markdown(md_text, output_format='html', extensions=self.extensions,
                             extension_configs=self.extension_configs)
        self.html = self.html.format(title, html_text)

        try:
            with open(html_path, 'w', encoding=self.encoding) as file_html:
                file_html.write(self.html)
        except Exception as error:
            print("<Error>", error)
            return False

        return True


if __name__ == '__main__':
    path = config.BASE_PATH + '/markdown2Html/'
    md_name = "result.md"
    html_name = "result.html"

    if mdtox(path + md_name).to_html(path + html_name):
        print('done')
