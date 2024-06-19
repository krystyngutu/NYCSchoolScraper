import fnmatch
import os

import requests
from lxml import html
from bs4 import BeautifulSoup
from datetime import datetime
from os.path import expanduser
import json
import time

def timer_func(func):
    """
    Decorator for logging function run-time as a performance counter
    """
    def wrap_func(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f'Function {func.__name__!r} executed in {(end-start):.4f}s')
        return result
    return wrap_func

@timer_func
def getSchoolUrls(pages):
    """
    Generate urls for each grouped collection of records in the school path
    :param pages: number of pages to request
    :return: list of urls
    """
    cachedLinkPath = os.path.join(f"{expanduser('~')}/schoolPages", 'links.json')
    if os.path.exists(cachedLinkPath):
        file = open(cachedLinkPath)
        linksJson = json.load(file)
        print(f"Found cached file of links: {cachedLinkPath}. Link count: {len(linksJson['links'])}")
        return linksJson['links'][:min(len(linksJson['links']), pages * 12)]


    baseUrl = 'https://nycmentors.org/schools'
    schoolsListItemPath = '//div[@class="schools-list__item"]/a/@href'
    allLinks = []
    cachedLinks = {}

    for currentPage in range(1, pages + 1):

        try:
            pageUrl = f'{baseUrl}?gad_source=1&gclid=CjwKCAjw34qzBhBmEiwAOUQcFzq8hETFXr4fNoJnSRyORnWkLdUvoLPG3PmjV3dqSXu8DfrilAmJXRoCTSMQAvD_BwE&page={currentPage}'
            linkResults = requests.get(pageUrl)
            tree = html.fromstring(linkResults.content)
            pageLinks = tree.xpath(schoolsListItemPath)

            if not pageLinks:
                break

            allLinks.extend(pageLinks)

        except Exception as e:
            print(f'${e}')
            break

    cachedLinks['links'] = allLinks
    with open(cachedLinkPath, 'w') as cacheFile:
        json.dump(cachedLinks, cacheFile)

    print(f"Saved link cache to {cachedLinkPath}. Link count: {len(allLinks)}")
    return allLinks

@timer_func
def getDom(schoolLink):
    """
    Retrieve school information page and return HTML tree
    :param schoolLink: URL to request
    :return: HTMLElement parsed from REST response
    """
    linkResults = requests.get(schoolLink)
    tree = html.fromstring(linkResults.content)
    return tree

def saveRequestResponsesToTextFile(schoolName, tree):
    """
    WIP: Cache the network responses per school
    :param schoolName:
    :param tree:
    :return:
    """
    try:
        with open(f'{os.path.join(expanduser("~/schoolPages"), f"{schoolName}.txt")}', 'w') as file:
            file.write(tree)

    except Exception as ex:
        print(f'{ex}')

def loadResponsesFromTextFile():
    """
    WIP: Load cached network responses per school
    :return: dictionary of school name to html string
    """
    try:
        loadedFiles = []
        for root, dirs, files in os.walk(f'{os.path.join(expanduser("~"), "/schoolPages")}'):
            for file in files:
                if fnmatch.fnmatch('*.txt', file):
                    loadedFiles.append(fil)

    except Exception as ex:
        print(f'{ex}')

def getSchoolName(tree):
    """
    Parse the school name from the tree
    :param tree: HTMLElement
    :return: string with school name
    """

    titleXpath = '//div[@class="school__info"]/h1[@class="school__title"]/text()'
    schoolName = tree.xpath(titleXpath)[0]

    return schoolName

def getGenderAndLunchInfo(tree):
    """
    Parse the gender breakdown and free/reduced lunch cost population
    :param tree: HTMLElement
    :return: dictionary of general topic (e.g., 'Gender') to nested dictionary of fields
    """
    try:
        schoolInfoDict = {}

        titleXpath = '//div[@class="school__params-item"]/text()'
        schoolInfo = tree.xpath(titleXpath)

        for info in schoolInfo:
            infoString = info.strip().replace('\n', '')

            if len(infoString) == 0:
                continue

            infoElements = infoString.split(':')
            infoField = infoElements[0].strip()
            infoValue = infoElements[1].strip()

            schoolInfoDict[infoField] = infoValue

        return schoolInfoDict

    except Exception as e:
        print(f'${e}')
        return {}

def getBarStats(tree):
    """
    Parse generic bar  data visualizations for relevant topics
    :param tree: HTMLElement
    :return: Dictionary of topics to nested dictionary of fields
    """
    try:
        groupPath = '//div[@class="school__stats-wrap"]'
        groupTitles = groupPath + '/div[@class="bar__group"]/h3[@class="school__stats-title"]/text()'

        groupFields = groupPath + '//div[@class="bar"]/div[@class="bar__header"]/span[@class="bar__name"]/text()'
        groupValues = groupPath + '//div[@class="bar"]/div[@class="bar__header"]/span[@class="bar__value"]/text()'

        titles = tree.xpath(groupTitles)
        fields = tree.xpath(groupFields)
        values = tree.xpath(groupValues)

        infoDict = {}

        fieldIdx = 0
        for titleIdx in range(len(titles)):
            firstField = None
            secondField = None
            firstValue = None
            secondValue = None

            if len(fields) > fieldIdx:
                firstField = fields[fieldIdx].strip()
            if len(values) > fieldIdx:
                textFirstValue = values[fieldIdx].strip()
                firstValue = int(textFirstValue.replace('%', '')) / 100

            if len(fields) > fieldIdx + 1:
                secondField = fields[fieldIdx + 1].strip()
            if len(values) > fieldIdx + 1:
                textSecondValue = values[fieldIdx + 1].strip()
                secondValue = int(textSecondValue.replace('%', '')) / 100

            infoDict[titles[titleIdx]] = {firstField: firstValue,
                                          secondField: secondValue}

            fieldIdx += 2

        return infoDict

    except Exception as e:
        print(f'${e}')
        return {}

def getChartStats(tree):
    """
    Parse generic bar  data visualizations for relevant topics
    :param tree: HTMLElement
    :return: Dictionary of topics to nested dictionary of fields
    """
    try:
        groupPath = '//div[@class="school__stats-wrap"]'
        groupTitles = groupPath + '/h3[@class="school__stats-title school__stats-title--chart"]/text()'

        enrollmentFieldPath = groupPath + '/div[@class="chart-bar js-barChart"]/@data-labels'
        enrollmentValuePath = groupPath + '/div[@class="chart-bar js-barChart"]/@data-values'
        ethnicityFieldPath = groupPath + '/div[@class="chart chart--1 js-doughnutChart"]/@data-labels'
        ethnicityValuePath = groupPath + '/div[@class="chart chart--1 js-doughnutChart"]/@data-values'
        stFieldPath = groupPath + '/div[@class="chart chart--2 js-doughnutChart"]/@data-labels'
        stValuePath = groupPath + '/div[@class="chart chart--2 js-doughnutChart"]/@data-values'

        titleIdx = 0
        titles = tree.xpath(groupTitles)
        enrollmentField = tree.xpath(enrollmentFieldPath)[0]
        enrollmentValue = tree.xpath(enrollmentValuePath)[0]
        ethnicityField = tree.xpath(ethnicityFieldPath)[0]
        ethnicityValue = tree.xpath(ethnicityValuePath)[0]
        stField = tree.xpath(stFieldPath)[0]
        stValue = tree.xpath(stValuePath)[0]

        statsDict = {}

        # Enrollment => {grade[] => num[]}
        # Ethnicity => {name[] => num[]}
        # S/T: ^

        enrollmentDict = dict()

        # parse labels into lists
        enrollmentFieldList = enrollmentField.split(',')
        enrollmentValueList = enrollmentValue.split(',')

        for fieldIdx in range(len(enrollmentFieldList)):

            # map field to value
            enrollmentField = enrollmentFieldList[fieldIdx]
            enrollmentValue = enrollmentValueList[fieldIdx]
            enrollmentDict[enrollmentField] = enrollmentValue

        # add title fields dict to stats
        statsDict[titles[titleIdx]] = enrollmentDict
        titleIdx += 1

        ethnicityDict = dict()

        # parse labels into lists
        ethnicityFieldList = ethnicityField.split(',')
        ethnicityValueList = ethnicityValue.split(',')

        for fieldIdx in range(len(ethnicityFieldList)):

            # map field to value
            ethnicityField = ethnicityFieldList[fieldIdx]
            ethnicityValue = ethnicityValueList[fieldIdx]
            ethnicityDict[ethnicityField] = ethnicityValue

        # add title fields dict to stats
        statsDict[titles[titleIdx]] = ethnicityDict
        titleIdx += 1

        stDict = dict()

        # parse labels into lists
        stFieldList = stField.split(',')
        stValueList = stValue.split(',')

        for fieldIdx in range(len(stFieldList)):

            # map field to value
            stField = stFieldList[fieldIdx]
            stValue = stValueList[fieldIdx]
            stDict[stField] = stValue

        # add title fields dict to stats
        statsDict[titles[titleIdx]] = stDict
        titleIdx += 1

        return statsDict

    except Exception as e:
        print(f'${e}')
        return {}

def writeOutput(outputJson, fullFilePath='./output.json'):
    """
    Write results to json file
    :param outputJson: JSON object containing parsed results
    :param fullFilePath: location to save file
    :return:
    """
    try:
        '''
        Ouput format:
        {
            [
                School => {
                    Title => {
                        Field => Value
                    }
                },
                ...
            ]
        }
        '''

        with open(fullFilePath, mode = 'w', encoding = 'utf-8') as file:
            json.dump(outputJson, file, ensure_ascii = False, indent = 4)

        print(f'Done writing to file {fullFilePath}.')

    except Exception as ex:
        print(f'{ex}')

def generateUniqueOutputFileName():
    """
    Generate a new and unique filename for new results using second-precision date-time and an atomically increasing file ID per second
    :return: string of file name
    """
    nameWithTime = f'{datetime.now().strftime("%Y%m%d%H%M%S")}'

    maxId = 0
    for root, dirs, files in os.walk(os.getcwd()):
        for file in files:
            if fnmatch.fnmatch(f'{nameWithTime}*', file):
                tokens = file.split('_')
                id = tokens[len(tokens) - 1]
                id = id.replace('.json', '')
                if maxId < int(id):
                    maxId = id

    return f'{nameWithTime}_{maxId + 1}'

if __name__ == '__main__':

    try:
        print(f"Started at {datetime.now().strftime('%H %M %S')}")
        schoolDict = {}

        schoolLinks = getSchoolUrls(pages = 20)
        print(schoolLinks)

        for link in schoolLinks:
            try:
                infoDict = dict()
                schoolDom = getDom(link)
                schoolName = getSchoolName(schoolDom)

                # saveRequestResponsesToTextFile(schoolName, schoolDom)
                schoolDict[schoolName] = infoDict
                infoDict['URL'] = link

                # populate info dict
                lunchAndGenderInfo = getGenderAndLunchInfo(schoolDom)
                for k, v in lunchAndGenderInfo.items():
                    infoDict[k] = v

                barStats = getBarStats(schoolDom)
                for k, v in barStats.items():
                    infoDict[k] = v

                chartStats = getChartStats(schoolDom)
                for k, v in chartStats.items():
                    infoDict[k] = v

            except Exception as ex:
                print(f'{ex} : {link}')

        outputFile = generateUniqueOutputFileName()
        path = os.path.join(os.getcwd(), f'{outputFile}_schoolScraper.json')

        writeOutput(schoolDict, fullFilePath=path)
    except Exception as ex:
        print(f'{ex}')
        exit(1)

    exit(0)