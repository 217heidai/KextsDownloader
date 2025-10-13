import os
import datetime

import httpx
from loguru import logger

class KEXT(object):
    def __init__(self, owner, repositories, latestUpdate, latestVersion, files):
        self.owner = owner
        self.repositories = repositories
        self.latestUpdate = latestUpdate
        self.latestVersion = latestVersion
        self.files = files

class DOWNLOADER(object):
    def __init__(self, kext:KEXT):
        self.__kext = kext
        self.__latestUpdate = ''
        self.__latestVersion = ''
        self.__files = []

        self.__client = httpx.Client(http2=True)

    def download(self):
        try:
            logger.info("download %s/%s..."%(self.__kext.owner, self.__kext.repositories))
            # 获取 release 信息
            url = "https://api.github.com/repos/%s/%s/releases"%(self.__kext.owner, self.__kext.repositories) # 不使用 /latest 接口，部分项目存在多重 release ，需所有 release 信息
            response = self.__client.get(url)
            response.raise_for_status()
            releaselist = response.json()
            for release in releaselist:
                tag = release.get("tag_name", None)
                assets = release.get("assets", [])
                if tag.find('alpha')>=0 or tag.find('RC')>=0 or len(assets) < 1: # 抛弃 alpha、RC 版本，无资源的 release
                    continue
                assets = release.get("assets", [])
                # 获取 release 文件资源
                for asset in assets:
                    fileName = asset.get("name", None)
                    if fileName.find('DEBUG')>=0 or fileName.find('debug')>=0 or fileName.find('Debug')>=0: # 抛弃 DEBUG 版本
                        continue
                    url = asset.get("browser_download_url", None)
                    self.__files.append("[%s](https://ghfast.top/%s)"%(fileName, url))
                    fileDate = datetime.datetime.strptime(asset.get("updated_at", ""), "%Y-%m-%dT%H:%M:%SZ")
                    fileDate = datetime.datetime.strftime(fileDate, '%Y%m%d')
                    self.__latestUpdate = fileDate
                    self.__latestVersion = tag
                
                if len(self.__files) > 0:
                    break
        except (Exception) as e:
            logger.exception("%s" % (e))
        finally:
            if len(self.__files) < 1: # 未获取到 release 资源，使用原有数据
                self.__latestUpdate = self.__kext.latestUpdate
                self.__latestVersion = self.__kext.latestVersion
                self.__files = self.__kext.files
            return KEXT(self.__kext.owner, self.__kext.repositories, self.__latestUpdate, self.__latestVersion, self.__files)

def GetKextsList():
    kextList = []
    with open('README.md', 'r', encoding='utf-8') as f:
        i = 0
        for line in f:
            if i > 1:
                info = line[1:-2].split("|")
                repositories = info[0].strip()
                repositories = repositories[repositories.find('[') + 1: repositories.find(']')]
                owner = info[1].strip()
                latestUpdate = info[2].strip()
                latestVersion = info[3].strip()
                files = info[4].strip().split(",")
                kextList.append(KEXT(owner, repositories, latestUpdate, latestVersion, files))
            i += 1
    return kextList

def CreatReadme(kextList):
    fileName = os.getcwd() + '/README.md'
    if os.path.exists(fileName):
        os.remove(fileName)
    with open(fileName, 'a') as f:
        f.write("| Repositories | Developer | Latest Update | Latest Version | Files                           |\n")
        f.write("|:-------------|:----------|:--------------|:---------------|:--------------------------------|\n")
        for kext in kextList:
            f.write("| [%s](https://github.com/%s/%s) | %s | %s | %s | %s |\n" % (kext.repositories, kext.owner, kext.repositories, kext.owner, kext.latestUpdate, kext.latestVersion, ",".join(kext.files)))

if __name__ == "__main__":
    kextList = GetKextsList()
    kextListNew = []
    for item in kextList:
        new = DOWNLOADER(item)
        kextListNew.append(new.download())

    # 生成README.md
    CreatReadme(kextListNew)
