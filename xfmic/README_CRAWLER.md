# 文档爬虫使用说明

## 功能介绍

这个爬虫脚本用于爬取 https://aiui-doc.xf-yun.com/project-1/doc-1/ 网站的所有文档页面，并按照左侧导航结构保存到本地。

## 安装依赖

```bash
pip install -r requirements.txt
```

或者单独安装：

```bash
pip install requests beautifulsoup4 urllib3 lxml
```

## 使用方法

### 方式1: 爬取导航链接（推荐）

这种方式只爬取左侧导航菜单中的链接，速度快，适合大多数场景：

```bash
python crawl_docs.py
```

### 方式2: 递归爬取所有链接

如果需要更全面的爬取，可以修改 `crawl_docs.py` 的 `main()` 函数，将：

```python
spider.crawl()
```

替换为：

```python
spider.crawl_recursive(max_depth=3)
```

然后运行：

```bash
python crawl_docs.py
```

## 输出结构

所有页面会保存到 `docs/` 文件夹下，文件路径对应页面的 URL 路径：

```
docs/
├── index.html              # 首页
├── _navigation.json        # 导航结构（JSON格式）
├── api/
│   ├── overview.html
│   └── reference.html
└── guide/
    ├── quickstart.html
    └── advanced.html
```

## 配置选项

可以在脚本中修改以下参数：

- `output_dir`: 输出目录，默认为 `docs`
- `max_depth`: 递归爬取的最大深度，默认为 3
- 请求延迟: 在 `time.sleep(0.5)` 处调整，单位为秒

## 注意事项

1. 脚本会自动处理 SSL 证书问题
2. 已访问的 URL 不会重复爬取
3. 每个请求之间会有 0.5 秒延迟，避免请求过快
4. 导航结构会保存在 `_navigation.json` 文件中

## 功能特性

- 自动识别左侧导航菜单
- 按照 URL 路径结构保存文件
- 支持中文路径和文件名
- 自动创建必要的目录结构
- 保存完整的 HTML 页面
- 导出导航结构为 JSON
