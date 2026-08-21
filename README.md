# surge-dae-dat

将 [SukkaW/Surge](https://github.com/SukkaW/Surge) 的规则自动转换为
dae 可读取的 V2Ray geodata `.dat` 文件。项目只使用 Python 标准库，不需要
Node.js、protobuf 编译器或额外运行时依赖。

## 快速开始

```bash
python3 -m surge_dae_dat build --output-dir dist
```

默认读取 `SukkaW/Surge@master` 的 `Source/domainset`、`Source/non_ip` 和
`Source/ip`，生成：

- `dist/surge-geosite.dat`：域名规则
- `dist/surge-geoip.dat`：`IP-CIDR`/`IP-CIDR6` 规则
- `dist/manifest.json`：源版本、源路径到 dat 标签的映射、条目数量、SHA-256
  和被跳过规则的警告

dae 配置示例：

```dae
domain(ext:"/etc/dae/surge-geosite.dat:reject") -> block
domain(ext:"/etc/dae/surge-geosite.dat:download") -> direct
dip(ext:"/etc/dae/surge-geoip.dat:reject") -> block
```

标签是源文件名（去掉 `.conf`，下划线改为短横线）。同名文件会自动加上
父目录前缀；完整标签可在 `manifest.json` 和构建日志中对应源路径。

## 本地规则和自动化

可以使用本地的 Surge checkout，构建时不会访问网络：

```bash
python3 -m surge_dae_dat build --source-dir /path/to/Surge --output-dir dist
```

仓库内的 `.github/workflows/build-rules.yml` 会在推送和每周定时任务中从上游拉取规则、运行测试，
然后将 `dist/` 产物上传到 R2；`dist/` 仅是临时构建目录，不会提交到 Git 历史。

启用该 workflow 需要配置以下 GitHub Actions secrets：

- `CLOUDFLARE_API_TOKEN`：具有目标 R2 bucket 对象读写权限的 API Token
- `CLOUDFLARE_ACCOUNT_ID`：Cloudflare Account ID
- `R2_BUCKET_NAME`：目标 R2 bucket 名称

## 规则兼容性

支持 `DOMAIN`、`DOMAIN-SUFFIX`、`DOMAIN-KEYWORD`、`DOMAIN-WILDCARD` 和
CIDR 规则。`URL-REGEX`、`GEOIP`、`IP-ASN`、进程/端口/协议等 Surge 规则没有
等价的 geodata 表达，会被跳过并记录在 manifest 的 `warnings` 中。通配符会
转换成锚定的正则；域名规则统一小写并去除末尾点，CIDR 会规范化为网络地址。

## 开发

```bash
python3 -m unittest discover -v
```

本项目代码按 AGPL-3.0-only 发布；上游 Surge 规则的版权和许可证请以其仓库
为准。
