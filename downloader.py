import os
import sys
import time

import requests
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport

class kext(object):
    def __init__(self, owner, repositories, latestUpdate, latestVersion, files):
        self.owner = owner 
        self.repositories = repositories
        self.latestUpdate = latestUpdate
        self.latestVersion = latestVersion
        self.files = files

class downloader(object):
    def __init__(self, kext, token):
        self.__owner = kext.owner
        self.__repositories = kext.repositories
        self.__latestUpdate = kext.latestUpdate
        self.__latestVersion = kext.latestVersion
        self.__files = kext.files
        self.__date = time.strftime("%Y/%m/%d", time.localtime())
        self.__transport = AIOHTTPTransport(url="https://api.github.com/graphql", headers={'Authorization': 'token ' + token})
        self.__client = Client(transport=self.__transport, fetch_schema_from_transport=True)

    def __findTag(self, dictData):
        queue = [dictData]
        while len(queue) > 0:
            data = queue.pop()
            for key, value in data.items():
                if key == 'nodes':
                    for item in value:
                        # print(type(item))
                        if 'tagName' in item.keys() and item['tagName'].find('alpha') < 0:
                            return item['tagName']
                elif type(value) == dict:
                    queue.append(value)
        return None

    def __findFileCount(self, dictData):
        queue = [dictData]
        while len(queue) > 0:
            data = queue.pop()
            for key, value in data.items():
                if key == 'totalCount':
                    return value
                elif type(value) == dict:
                    queue.append(value)
        return None

    def __findFileNameAndUrl(self, dictData):
        fileList = {}
        queue = [dictData]
        while len(queue) > 0:
            data = queue.pop()
            for key, value in data.items():
                if key == 'nodes':
                    for item in value:
                        fileList[item['name']] = item['downloadUrl']
                elif type(value) == dict:
                    queue.append(value)
        return fileList

    def __queryLatestTag(self):
        query = gql(
            """
            query {
                repository(name: "%s", owner: "%s") {
                    releases(first: 2, orderBy: {field: CREATED_AT, direction: DESC}) {
                        nodes {
                            tagName
                        }
                    }
                }
            }
            """ % (self.__repositories, self.__owner)
        )

        try:
            result = self.__client.execute(query)
            #print(result)
            tag = self.__findTag(result)
            if tag is None:
                raise Exception("Can't find 'tagName'")
            # print(tag)
            return tag
        except (Exception) as e:
            print('ERROR:', e)

    def __queryReleasesFileCount(self, tagName):
        # Provide a GraphQL query
        query = gql(
            """
            query {
                repository(name: "%s", owner: "%s") {
                    release(tagName: "%s") {
                        releaseAssets{
                            totalCount
                        }
                    }
                }
            }
            """ % (self.__repositories, self.__owner, tagName)
        )

        # Execute the query on the transport
        try:
            result = self.__client.execute(query)
            # print(result)
            totalCount = self.__findFileCount(result)
            if totalCount is None:
                raise Exception("Can't find 'totalCount'")
            # print(totalCount)
            return totalCount
        except (Exception) as e:
            print('ERROR:', e)

    def __queryReleasesFile(self, tagName, fileCount):
        # Provide a GraphQL query
        query = gql(
            """
            query {
                repository(name: "%s", owner: "%s") {
                    release(tagName: "%s") {
                        releaseAssets(first: %s) {
                            nodes {
                                downloadUrl
                                name
                            }
                        }
                    }
                }
            }
            """ % (self.__repositories, self.__owner, tagName, fileCount)
        )

        # Execute the query on the transport
        try:
            result = self.__client.execute(query)
            # print(result)
            return self.__findFileNameAndUrl(result)
        except (Exception) as e:
            print('ERROR:', e)

    def download(self):
        print("\n\nKext Repositories: %s/%s" %
              (self.__owner, self.__repositories))
        try:
            tag = self.__queryLatestTag()
            print("Release tag: %s" % (tag))
            if tag > self.__latestVersion :
                # 删除老文件
                RemoveKexts(self.__files)
                files = ''

                # 下载新文件
                FileCount = self.__queryReleasesFileCount(tag)
                fileList = self.__queryReleasesFile(tag, FileCount)
                print(fileList)
                pwd = os.getcwd()
                for key,value in fileList.items():
                    print("File: %s\nURL: %s" % (key, value))
                    #https://shrill-pond-3e81.hunsh.workers.dev/https://github.com/217heidai/openssl_for_android/releases/download/1.1.1j/OpenSSL_1.1.1j_arm64-v8a.tar.gz
                    r = requests.get(value)
                    if key.find('OpenCore') >= 0:
                        path = '/OpenCore/'
                    else:
                        path = '/Kexts/'
                    with open(pwd + path + key, "wb") as code:
                        code.write(r.content)
                     # 更新files
                    if len(files) > 0:
                        files += ', '
                    files += '[' + key + '](https://cdn.jsdelivr.net/gh/217heidai/KextsDownloader@main' + path + key + ')'
                
                # 更新latestUpdate
                self.__latestUpdate = self.__date
                # 更新latestVersion
                self.__latestVersion = tag
                # 更新files
                self.__files = files
        except (Exception) as e:
            print('ERROR:', e)
        finally:
            return kext(self.__owner, self.__repositories, self.__latestUpdate, self.__latestVersion, self.__files)

def RemoveKexts(files):
    try:
        pwd = os.getcwd()
        if os.path.exists(pwd + '/README.md'):
            os.remove(pwd + '/README.md')

        if not os.path.exists(pwd + '/OpenCore'):
            os.mkdir(pwd + '/OpenCore')
        if not os.path.exists(pwd + '/Kexts'):
            os.mkdir(pwd + '/Kexts')

        # [AppleALC-1.5.7-DEBUG.zip](https://github.com/acidanthera/AppleALC/releases/download/1.5.7/AppleALC-1.5.7-DEBUG.zip), [AppleALC-1.5.7-RELEASE.zip'](https://github.com/acidanthera/AppleALC/releases/download/1.5.7/AppleALC-1.5.7-RELEASE.zip)
        fileList = files.split(", ")
        for item in fileList:
            name = item[item.find('[') + 1:item.find(']')]
            if name.find('OpenCore') >= 0:
                path = pwd + '/OpenCore/' + name
            else:
                path = pwd + '/Kexts/' + name
            if os.path.exists(path):
                os.remove(path)
    except (Exception) as e:
        print('ERROR:', e)

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
                files = info[4].strip()
                kextList.append(kext(owner, repositories, latestUpdate, latestVersion, files))
            i += 1
    return kextList

def CreatReadme(kextList):
    pwd = os.getcwd()
    if not os.path.exists(pwd + '/README.md'):
        f = open(pwd + '/README.md', 'a')
        f.write("| Repositories | Developer | Latest Update | Latest Version | Files                           |\n")
        f.write("|:-------------|:----------|:--------------|:---------------|:--------------------------------|\n")
        for kext in kextList:
            f.write("| [%s](https://github.com/%s/%s) | %s | %s | %s | %s |\n" % (kext.repositories, kext.owner, kext.repositories, kext.owner, kext.latestUpdate, kext.latestVersion, kext.files))
        f.close()

if __name__ == "__main__":
    tocken = sys.argv[1]
    kextList = GetKextsList()
    kextListNew = []
    for item in kextList:
        try:
            new = downloader(item, tocken)
            kextListNew.append(new.download())
        except (Exception) as e:
            print('ERROR:', e)

    # 生成README.md
    CreatReadme(kextListNew)