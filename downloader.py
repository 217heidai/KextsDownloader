import os
import sys

import requests
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport

class kext(object):
    def __init__(self, owner, repositories, latestRelease, files):
        self.owner = owner 
        self.repositories = repositories
        self.latestRelease = latestRelease
        self.files = files


class downloader(object):
    def __init__(self, kext, token):
        self.__owner = kext.owner
        self.__repositories = kext.repositories
        self.__latestRelease = kext.latestRelease
        self.__files = kext.files
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
                    releases(first: 1, orderBy: {field: CREATED_AT, direction: DESC}) {
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
            if tag > self.__latestRelease :
                # 删除老文件
                RemoveKexts(self.__files)
                self.__files = ''

                # 下载新文件
                FileCount = self.__queryReleasesFileCount(tag)
                fileList = self.__queryReleasesFile(tag, FileCount)
                print(fileList)
                for key,value in fileList.items():
                    print("File: %s\nURL: %s" % (key, value))
                    r = requests.get(value)
                    with open(key, "wb") as code:
                        code.write(r.content)
                     # 更新files
                    if len(self.__files) > 0:
                        self.__files += ', '
                    self.__files += '[' + key + '](https://cdn.jsdelivr.net/gh/217heidai/KextsDownloader@main/' + key + ')'
                
                # 更新latestRelease
                self.__latestRelease = tag

            return kext(self.__owner, self.__repositories, self.__latestRelease, self.__files)

        except (Exception) as e:
            print('ERROR:', e)
            return kext(self.__owner, self.__repositories, ' ', ' ')

def RemoveKexts(files):
    if os.path.exists('README.md'):
        os.remove('README.md')

    # [AppleALC-1.5.7-DEBUG.zip](https://github.com/acidanthera/AppleALC/releases/download/1.5.7/AppleALC-1.5.7-DEBUG.zip), [AppleALC-1.5.7-RELEASE.zip'](https://github.com/acidanthera/AppleALC/releases/download/1.5.7/AppleALC-1.5.7-RELEASE.zip)
    fileList = files.split(", ")
    for item in fileList:
        name = item[item.find('['):item.find(']')]
        if os.path.exists(name):
            os.remove(name)

def GetKextsList():
    kextList = []
    with open('README.md', 'r', encoding='utf-8') as f:
        i = 0
        for line in f:
            if i > 1:
                info = line[1:-2].split("|")
                repositories = info[0].strip()
                owner = info[1].strip()
                latestRelease = info[2].strip()
                files = info[3].strip()
                kextList.append(kext(owner, repositories, latestRelease, files))
            i += 1
    return kextList

def CreatReadme(kextList):
    if not os.path.exists('README.md'):
        f = open('README.md', 'a')
        f.write("| Repositories | Owner | Latest release | Files                           |\n")
        f.write("|:-------------|:------|:---------------|:--------------------------------|\n")
        for kext in kextList:
            f.write("| %s | %s | %s | %s |\n" % (kext.repositories, kext.owner, kext.latestRelease, kext.files))
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