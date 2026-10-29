# coding=utf-8
"""
服务器报表/配置文件 (zhb.zip) 下载与解压

通达信板块/配置文件以 zhb.zip 总包经 0x06b9 报表协议整体下发, 内含 44 个文件:
  tdxzs.cfg  板块名↔指数代码(id)
  tdxbk.cfg  板块简称↔全称
  tdxstat.cfg 个股统计/资金流向字段
  xgsg.cfg   新股申购
  spblock.dat 大型指数成分(中证2000等, 无上限)
  incon.dat, tdxhy.cfg, ... 等

下载走 pytdx 已有的 get_report_file_by_size (0x06b9), 本模块负责解压与文件分发,
为后续各文件格式解析器提供基础。
"""

import io
import zipfile


ZHB_FILENAME = 'zhb.zip'


def download_zhb_zip(api, reporthook=None):
    """通过 0x06b9 协议下载 zhb.zip 完整字节"""
    return api.get_report_file_by_size(ZHB_FILENAME, filesize=0, reporthook=reporthook)


def extract_zhb(zip_bytes):
    """解压 zhb.zip, 返回 {文件名: 字节内容}"""
    files = {}
    with zipfile.ZipFile(io.BytesIO(bytes(zip_bytes))) as zf:
        for name in zf.namelist():
            files[name] = zf.read(name)
    return files


def get_zhb_files(api, reporthook=None):
    """一步到位: 下载 zhb.zip 并解压, 返回 {文件名: 字节内容}"""
    raw = download_zhb_zip(api, reporthook=reporthook)
    return extract_zhb(raw)
