# -*- coding: utf-8 -*-
"""
压缩静态资源文件，优化页面加载速度
"""
import os
import re

def compress_css(css_content):
    """压缩CSS内容"""
    # 移除注释
    css_content = re.sub(r'/\*[\s\S]*?\*/', '', css_content)
    # 移除多余的空白字符
    css_content = re.sub(r'\s+', ' ', css_content)
    # 移除分号和大括号周围的空白
    css_content = re.sub(r'\s*([{}:;])\s*', '\1', css_content)
    # 移除行尾分号（某些情况下）
    css_content = re.sub(r';\s*}', '}', css_content)
    return css_content

def compress_js(js_content):
    """简单压缩JavaScript内容"""
    # 移除注释
    js_content = re.sub(r'//.*$', '', js_content, flags=re.MULTILINE)
    js_content = re.sub(r'/\*[\s\S]*?\*/', '', js_content)
    # 移除多余的空白字符
    js_content = re.sub(r'\s+', ' ', js_content)
    # 移除分号和大括号周围的空白
    js_content = re.sub(r'\s*([{}:;()\[\]])\s*', '\1', js_content)
    return js_content

def main():
    """主函数"""
    # 压缩CSS文件
    css_path = 'static/css/style.css'
    if os.path.exists(css_path):
        with open(css_path, 'r', encoding='utf-8') as f:
            css_content = f.read()
        compressed_css = compress_css(css_content)
        with open('static/css/style.min.css', 'w', encoding='utf-8') as f:
            f.write(compressed_css)
        print(f'CSS压缩完成: {len(compressed_css)} bytes (原始: {len(css_content)} bytes)')
    else:
        print(f'CSS文件不存在: {css_path}')
    
    # 压缩JavaScript文件
    js_path = 'static/js/main.js'
    if os.path.exists(js_path):
        with open(js_path, 'r', encoding='utf-8') as f:
            js_content = f.read()
        compressed_js = compress_js(js_content)
        with open('static/js/main.min.js', 'w', encoding='utf-8') as f:
            f.write(compressed_js)
        print(f'JavaScript压缩完成: {len(compressed_js)} bytes (原始: {len(js_content)} bytes)')
    else:
        print(f'JavaScript文件不存在: {js_path}')

if __name__ == '__main__':
    main()
