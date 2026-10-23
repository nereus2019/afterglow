# 余味 · 私人作品书架

当前版本：1.1。新增分册与跨语言检索、MusicBrainz 专辑来源、iTunes 台湾/美国区域检索、月度统计。

## 从 1.0 升级

先在旧版页面导出 JSON 备份，停止旧版服务，再将新版解压到一个新文件夹并启动，导入备份即可。旧版没有“停止余味.cmd”时可重启电脑后直接启动新版。不要同时运行两个文件夹的服务：默认端口相同，可能打开的仍是旧版。

本地运行的个人作品记录工具，支持电影、电视剧、综艺、书籍、游戏与专辑。电脑、手机浏览器使用响应式界面，连接同一台电脑时共用 SQLite 数据库。

## 启动

Windows 双击 `启动余味.cmd`。脚本确认服务就绪后自动打开 http://127.0.0.1:8765 ，服务在后台运行，关闭网页不影响服务。重复启动会直接打开已有服务。电脑重启后需要再次双击启动文件。

启动脚本优先使用本机 Codex 自带 Python，其他电脑需安装 Python 3.10 或以上，无需安装第三方依赖。也可以在此目录执行 `python server.py`。

## 手机访问

1. 手机与电脑连接同一个 Wi-Fi。
2. 点击页面左下角（手机布局右上角）的“在手机上打开”，将显示的局域网地址输入手机浏览器。
3. 如果显示多个地址，选择电脑当前 Wi-Fi 对应的地址。若无法访问，请允许 Python 通过 Windows 防火墙的“专用网络”，并确认路由器没有启用客户端隔离。

电脑需要持续开机运行工具。手机没有独立数据库，不支持脱离电脑使用或公网云同步。应用没有登录系统，仅应在可信局域网使用，不要做公网端口映射。

## 功能

- 搜索作品、查看来源链接、选择版本、编辑分类后标记；支持手动补录。
- 自动记录当天日期，可修改历史日期、作品名称、年份/版本、封面链接及感想。
- 分类统计、书架搜索、日期或名称排序、修改与删除。
- 月度统计：按标记日期统计所选年份的 12 个月，包含六种分类及合计。点击月份可筛选书架，点击“查看全部月份”取消筛选。每条记录计 1 部，独立分册分别计数；套书条目整体计 1 部，不自动拆成多册。统计不受当前书架分类或关键词筛选影响，也不记录同一作品的多次重看事件。
- JSON 完整导出与合并恢复：重复 ID 或同分类同来源作品跳过，不覆盖现有记录。手动记录按分类与名称去重；不同来源的同一作品需自行核对。
- CSV 导出，兼容 Excel UTF-8；CSV 仅用于查看，不用于恢复。

## 数据与搜索

数据文件：`data/library.sqlite3`。关闭服务后可以复制整个 `data` 文件夹；日常推荐在页面导出 JSON 备份。备份包括作品元数据、标记日期与感想，不包含图片。图片引用远程地址，离线或加载失败时显示文字封面；已保存的记录仍可查看编辑。

搜索来源：
- 书籍：Bangumi、Open Library、深空出版公开目录。出版社来源仅覆盖该社，不代表全部中文出版物。单册、套书、特装版分别显示，保留源条目 ID，避免把不同分册合并。Open Library 书目可能包含不同语种版本，小说与漫画请结合作者和来源核对。
- 专辑：MusicBrainz、iTunes 台湾/美国区、Bangumi。MusicBrainz 不依赖作品是否在某个流媒体平台上架；同名不同艺人的专辑分别保留。Spotify 官方搜索需要 OAuth 授权，本版未接入 Spotify，不需要 Spotify 账号。
- 其他分类：Bangumi 与中文 Wikipedia。Wikipedia 是通用检索，Bangumi 的影视类型也较宽，请核对具体分类。

Windows 上自动尝试繁简体。书籍在 Bangumi 精确匹配标题后读取其原名与英文别名，并交给 Open Library 补充检索；不是任意名称的机器翻译。对“全能读者视角”增加了常用标题“全知读者视角”的纠正，其余名称来自实时目录或用户手填的“其他译名”。分册元数据不通过编号猜测生成。没有搜到时可以补充英文/原文名，或手动添加。

搜索结果支持按来源以及卷号、作者、年份、版本筛选。每次查询各源最多返回 20–100 条，页面会显示实际检索名称、各来源结果数与失败提示；这不保证穷尽整套作品。重复查询缓存 10 分钟，各服务串行限速以减少限流。关键词会发送给对应公开服务，均无需用户填写 API 密钥。网络或来源收录差异仍可能导致缺项。

接口参考：
- https://bangumi.github.io/api/
- https://openlibrary.org/dev/docs/api/search
- https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/
- https://www.mediawiki.org/wiki/API:Search
- https://www.starwatcher.com.tw/product/orv001/
- https://developer.woocommerce.com/docs/apis/store-api/resources-endpoints/products/
- https://musicbrainz.org/doc/MusicBrainz_API
- https://developer.spotify.com/documentation/web-api/concepts/api-calls

## 验证

`python -m unittest discover -s tests -v`

`node tests/test_stats.cjs` 验证月度统计；`python tests/verify_portable.py` 从新版 ZIP 独立解压验证启动、保存与备份恢复。

测试使用临时数据库，覆盖持久化、去重、编辑、导入失败回滚、合并恢复与 HTTP 读写保护，不会修改个人数据。

自定义端口：启动前设置环境变量 `PORT`。自定义数据库路径：设置 `AFTERGLOW_DB`。默认监听局域网所有网卡的 8765 端口。
