#!/usr/bin/env python3
"""
文档网站爬虫脚本
爬取 https://aiui-doc.xf-yun.com/project-1/doc-1/ 的所有文档页面
按照左侧导航结构保存到 docs 文件夹
"""

import os
import re
import time
from urllib.parse import urljoin, urlparse, unquote
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import json

# 禁用 SSL 警告
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class DocsSpider:
    def __init__(self, base_url, output_dir='docs'):
        self.base_url = base_url.rstrip('/')
        self.output_dir = output_dir
        self.visited_urls = set()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        # 导航结构
        self.nav_structure = []

    def get_page(self, url):
        """获取页面内容"""
        try:
            print(f"正在获取: {url}")
            response = self.session.get(url, verify=False, timeout=30)
            response.encoding = response.apparent_encoding
            return response.text
        except Exception as e:
            print(f"获取页面失败 {url}: {e}")
            return None

    def parse_navigation(self, html):
        """解析左侧导航菜单"""
        soup = BeautifulSoup(html, 'html.parser')
        nav_links = []

        # 查找导航元素
        nav_element = soup.select_one('nav ul.summary')

        if nav_element:
            print(f"找到导航元素: nav ul.summary")
        else:
            # 如果找不到，尝试其他选择器
            nav_selectors = [
                '.sidebar nav',
                '.sidebar',
                'nav.menu',
                '.doc-nav',
                '#sidebar',
                '.doc-summary nav',
                '[class*="sidebar"]',
                '[class*="navigation"]',
            ]

            for selector in nav_selectors:
                nav_element = soup.select_one(selector)
                if nav_element:
                    print(f"找到导航元素，使用选择器: {selector}")
                    break

        if not nav_element:
            # 如果找不到导航，尝试找所有链接
            print("未找到特定导航元素，尝试获取所有内部链接")
            nav_element = soup

        # 提取所有链接
        for link in nav_element.find_all('a', href=True):
            href = link['href']
            text = link.get_text(strip=True)

            # 跳过空文本或搜索链接
            if not text or 'kw=' in href:
                continue

            # 构建完整 URL
            full_url = urljoin(self.base_url, href)

            # 只处理 /project-1/doc-* 格式的文档链接
            parsed_url = urlparse(full_url)
            if '/project-1/doc-' in parsed_url.path:
                # 去除重复链接
                if not any(link['url'] == full_url for link in nav_links):
                    nav_links.append({
                        'url': full_url,
                        'text': text,
                        'href': href
                    })

        return nav_links

    def get_file_path(self, url):
        """根据 URL 生成文件路径"""
        # 解析 URL
        parsed = urlparse(url)
        path = parsed.path

        # 移除基础路径
        base_path = urlparse(self.base_url).path
        if path.startswith(base_path):
            path = path[len(base_path):]

        # 清理路径
        path = path.strip('/')

        # 如果路径为空，使用 index
        if not path:
            path = 'index'

        # URL 解码
        path = unquote(path)

        # 替换不安全的文件名字符
        path = re.sub(r'[<>:"|?*]', '_', path)

        # 如果以斜杠结尾，添加 index
        if path.endswith('/'):
            path += 'index'

        # 添加 .html 扩展名
        if not path.endswith('.html'):
            path += '.html'

        return os.path.join(self.output_dir, path)

    def save_page(self, url, html):
        """保存页面到文件"""
        file_path = self.get_file_path(url)

        # 创建目录
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # 保存 HTML
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"已保存: {file_path}")
        return file_path

    def extract_content(self, html):
        """提取页面主要内容"""
        soup = BeautifulSoup(html, 'html.parser')

        # 尝试找到主要内容区域
        content_selectors = [
            'main',
            '.content',
            '.main-content',
            '.doc-content',
            'article',
            '[role="main"]',
            '#content',
            '[class*="content"]'
        ]

        content = None
        for selector in content_selectors:
            content = soup.select_one(selector)
            if content:
                break

        if not content:
            # 如果找不到特定内容区域，使用 body
            content = soup.find('body')

        return content

    def crawl(self):
        """开始爬取"""
        print(f"开始爬取: {self.base_url}")
        print(f"输出目录: {self.output_dir}")

        # 创建输出目录
        os.makedirs(self.output_dir, exist_ok=True)

        # 获取首页
        html = self.get_page(self.base_url)
        if not html:
            print("无法获取首页")
            return

        # 保存首页
        self.save_page(self.base_url, html)
        self.visited_urls.add(self.base_url)

        # 解析导航
        nav_links = self.parse_navigation(html)
        print(f"\n找到 {len(nav_links)} 个导航链接")

        # 保存导航结构
        with open(os.path.join(self.output_dir, '_navigation.json'), 'w', encoding='utf-8') as f:
            json.dump(nav_links, f, ensure_ascii=False, indent=2)

        # 爬取所有导航链接
        for i, link in enumerate(nav_links, 1):
            url = link['url']

            if url in self.visited_urls:
                continue

            print(f"\n[{i}/{len(nav_links)}] 处理: {link['text']}")

            # 获取页面
            html = self.get_page(url)
            if html:
                # 保存页面
                self.save_page(url, html)
                self.visited_urls.add(url)

                # 休眠避免请求过快
                time.sleep(0.5)

        print(f"\n爬取完成！共处理 {len(self.visited_urls)} 个页面")
        print(f"文件保存在: {os.path.abspath(self.output_dir)}")

    def crawl_recursive(self, max_depth=3):
        """递归爬取所有链接"""
        print(f"开始递归爬取: {self.base_url} (最大深度: {max_depth})")
        print(f"输出目录: {self.output_dir}")

        # 创建输出目录
        os.makedirs(self.output_dir, exist_ok=True)

        # 待处理的 URL 队列 (url, depth)
        queue = [(self.base_url, 0)]

        while queue:
            url, depth = queue.pop(0)

            if url in self.visited_urls:
                continue

            if depth > max_depth:
                continue

            print(f"\n[深度 {depth}] 正在处理: {url}")

            # 获取页面
            html = self.get_page(url)
            if not html:
                continue

            # 保存页面
            self.save_page(url, html)
            self.visited_urls.add(url)

            # 如果还没达到最大深度，提取链接继续爬取
            if depth < max_depth:
                soup = BeautifulSoup(html, 'html.parser')
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    full_url = urljoin(url, href)

                    # 只处理同域名的链接
                    if full_url.startswith(self.base_url) and full_url not in self.visited_urls:
                        queue.append((full_url, depth + 1))

            # 休眠避免请求过快
            time.sleep(0.5)

        print(f"\n爬取完成！共处理 {len(self.visited_urls)} 个页面")
        print(f"文件保存在: {os.path.abspath(self.output_dir)}")


def main():
    # 目标网站
    base_url = 'https://aiui-doc.xf-yun.com/project-1/doc-1/'

    # 创建爬虫实例
    spider = DocsSpider(base_url, output_dir='docs')

    # 方式1: 只爬取导航链接（推荐，更快）
    spider.crawl()

    # 方式2: 递归爬取所有链接（更全面，但可能较慢）
    # spider.crawl_recursive(max_depth=3)


if __name__ == '__main__':
    main()
