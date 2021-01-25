import os

import requests
import asyncio
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport

TOKEN = ''

class downloader(object):
    # Select your transport with a defined url endpoint
    transport = AIOHTTPTransport(url="https://api.github.com/graphql", headers={'Authorization': 'token %s'%(TOKEN)})

    # Create a GraphQL client using the defined transport
    client = Client(transport=transport, fetch_schema_from_transport=True)

    def __init__(self, owner, repositories):
        self.__owner = owner
        self.__repositories = repositories

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
        queue = [dictData]
        while len(queue) > 0:
            data = queue.pop()
            for key, value in data.items():
                if key == 'nodes':
                    for item in value:
                        if len(value) == 1:
                            return item['name'], item['downloadUrl']
                        if item['name'].find('RELEASE') >= 0 or item['name'].find('Release') >= 0 or item['name'].find('release') >= 0 or item['name'].find('Big_Sur') >= 0 or item['name'].find('BigSur') >= 0:
                            return item['name'], item['downloadUrl']
                elif type(value) == dict:
                    queue.append(value)
        return None

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
            result = self.client.execute(query)
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
            result = self.client.execute(query)
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
                                size
                            }
                        }
                    }
                }
            }
            """ % (self.__repositories, self.__owner, tagName, fileCount)
        )

        # Execute the query on the transport
        try:
            result = self.client.execute(query)
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
            FileCount = self.__queryReleasesFileCount(tag)
            name, url = self.__queryReleasesFile(tag, FileCount)
            print("File name: %s\nURL: %s" % (name, url))
            r = requests.get(url)
            with open(name, "wb") as code:
                code.write(r.content)
        except (Exception) as e:
            print('ERROR:', e)


class kext(object):
    def __init__(self, owner, repositories):
        self.owner = owner
        self.repositories = repositories


def RemoveKexts():  # 获取csv文件list
    kextsList = []
    for root, dirs, files in os.walk(os.getcwd()):
        for kext in files:
            if os.path.splitext(kext)[1] == '.zip':
                kextsList.append(os.path.join(root, kext))
    for kext in kextsList:
        os.remove(kext)

if __name__ == "__main__":
    TOKEN = sys.argv[1]
    RemoveKexts()
    kextList = []
    kextList.append(kext('acidanthera', 'AppleALC'))
    kextList.append(kext('acidanthera', 'IntelMausi'))
    kextList.append(kext('acidanthera', 'Lilu'))
    kextList.append(kext('acidanthera', 'NVMeFix'))
    kextList.append(kext('acidanthera', 'VirtualSMC'))
    kextList.append(kext('acidanthera', 'WhateverGreen'))
    kextList.append(kext('acidanthera', 'BrightnessKeys'))
    kextList.append(kext('acidanthera', 'VoodooInput'))
    kextList.append(kext('acidanthera', 'VoodooPS2'))
    kextList.append(kext('Sniki', 'OS-X-USB-Inject-All'))
    kextList.append(kext('Mieze', 'RTL8111_driver_for_OS_X'))
    kextList.append(kext('VoodooI2C', 'VoodooI2C'))
    kextList.append(kext('OpenIntelWireless', 'IntelBluetoothFirmware'))
    kextList.append(kext('OpenIntelWireless', 'itlwm'))

    for item in kextList:
        try:
            new = downloader(item.owner, item.repositories)
            new.download()
        except (Exception) as e:
            print('ERROR:', e)
