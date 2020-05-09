import json
import math
import requests
from datetime import datetime

baseUrl = "https://api.nexushub.co/wow-classic/v1/items/"
datetimeFormat = '%Y-%m-%dT%X.000Z'

def calculateSellToVendor(craftList, profession, server, faction):
    # Import apropriate list of recipes
    if profession == "Alchemy":
        f = open("app/data/alchemy.json", 'r')
    elif profession == "Blacksmithing":
        f = open("app/data/blacksmithing.json", 'r')
    elif profession == "Cooking":
        f = open("app/data/cooking.json", 'r')
    elif profession == "Enchanting":
        return 0
    elif profession == "Engineering":
        f = open("app/data/engineering.json", 'r')
    elif profession == "Leatherworking":
        f = open("app/data/leatherworking.json", 'r')
    else:
        f = open("app/data/tailoring.json", 'r')

    recipes = json.load(f)

    totalMoneyGained = 0
    serverUrl = baseUrl + server[3:].replace(' ', '-').lower() + '-' + faction.lower() + '/'
    for index, info in craftList.items():
        requestUrl = serverUrl + str(recipes[info["Recipe"]]["ID"])
        response = requests.get(requestUrl)
        responseJson = response.json()

        if "sellPrice" in responseJson:
            sellPrice = int(responseJson["sellPrice"])
        else:
            sellPrice = 0
        totalMoneyGained += sellPrice*info["Count"]

    return totalMoneyGained

def calculateRecipePrices(recipes, prices):
    recipePriceDict = dict()

    for name, info in recipes.items():
        price = 0
        usable = True
        for reagent, amount in info["Reagents"].items():
            # If a reagent doesn't have a determinable price
            if reagent not in prices:
                # Set flag to not add the recipe to the output dict
                usable = False
            else:
                price += amount*prices[reagent]["Price"]
        
        if usable:
            recipePriceDict[name] = price
    
    return recipePriceDict

def calculateReagentCost(reagents, prices):
    reagentCost = 0
    for reagent, info in reagents.items():
        reagentCost += info["Amount"]*prices[reagent]["Price"]

    return reagentCost

def searchCraftList(craftList, target):
    return [index for index, data in craftList.items() if data["Recipe"] == target]

def getCheapestSkillingRecipe(recipes, recipePrices, currentSkill):
    cost = 999999 # arbitrary large number
    candidate = ''

    for name, info in recipes.items():
        if info["Learn"] <= currentSkill:
            if recipePrices[name] < cost:
                candidate = name
                cost = recipePrices[name]

    return candidate
    
def getReagentPrices(recipes, server, faction):
    # Import translation table for item name to ID
    with open("app/data/itemID.json", 'r') as f:
            itemID = json.load(f)

    # Make a set of all potential reagents
    reagents = set()
    for info in recipes.values():
        for reagent in info["Reagents"].keys():
            reagents.add(reagent)
    
    # Iterate over the reagent set and create a dictionary containing reagent-price pairs
    reagentPriceDict = dict()
    serverUrl = baseUrl + server[3:].replace(' ', '-').lower() + '-' + faction.lower() + '/'
    for reagent in reagents:
        requestUrl = serverUrl + str(itemID[reagent])
        response = requests.get(requestUrl)
        responseJson = response.json()
        
        # If item cant be bought from vendor
        if responseJson["vendorPrice"] == None:
            # If no price data exists, i.e. item hasn't been seen on the AH
            if responseJson["stats"]["current"] == None:
                # Don't add the reagent to the output dict, i.e. noop
                pass
            else:
                reagentPriceDict[reagent] = dict()
                reagentPriceDict[reagent]["Price"] = responseJson["stats"]["current"]["marketValue"]
                reagentPriceDict[reagent]["Quantity"] = responseJson["stats"]["current"]["quantity"]
                datetimeStr = responseJson["stats"]["lastUpdated"]
                datetimeObj = datetime.strptime(datetimeStr, datetimeFormat)
                reagentPriceDict[reagent]["LastSeen"] = datetimeObj
        # Item can be bought from vendor, use the vendor price
        else:
            reagentPriceDict[reagent] = dict()
            reagentPriceDict[reagent]["Price"] = responseJson["vendorPrice"]
            reagentPriceDict[reagent]["Quantity"] = None
            reagentPriceDict[reagent]["LastSeen"] = datetime.now()

    return reagentPriceDict

def getRecipePrice(recipeID, server, faction):
    serverUrl = baseUrl + server[3:].replace(' ', '-').lower() + '-' + faction.lower() + '/'
    requestUrl = serverUrl + str(recipeID)
    response = requests.get(requestUrl)
    responseJson = response.json()

    if responseJson["stats"]["current"] == None:
        return 0
    else:
        return responseJson["stats"]["current"]["marketValue"]

def importRecipes(profession, targetSkill, recipeSources, faction, school):
    # Import apropriate list of recipes
    if profession == "Alchemy":
        f = open("app/data/alchemy.json", 'r')
    elif profession == "Blacksmithing":
        f = open("app/data/blacksmithing.json", 'r')
    elif profession == "Cooking":
        f = open("app/data/cooking.json", 'r')
    elif profession == "Enchanting":
        f = open("app/data/enchanting.json", 'r')
    elif profession == "Engineering":
        f = open("app/data/engineering.json", 'r')
    elif profession == "Leatherworking":
        f = open("app/data/leatherworking.json", 'r')
    else:
        f = open("app/data/tailoring.json", 'r')

    recipes = json.load(f)
    
    # Remove recipes from upcoming phases
    temp = recipes.copy()
    for name, info in temp.items():
        if not "Learn" in info:
            recipes.pop(name)

    # Remove recipes that are learned past our target skill
    temp = recipes.copy()
    for name, info in temp.items():
        if info["Learn"] >= targetSkill:
            recipes.pop(name)

    # Remove recipes from unwanted sources
    # Iterate over the different sources
    for source, value in recipeSources.items():
        # If a source has the value "False"
        if not value:
            # Iterate over the recipe dictionary and remove all recipes with the specified source
            temp = recipes.copy()
            for name, info in temp.items():
                if info["Source"] == source:
                    recipes.pop(name)

    # Remove recipes from conflicting schools
    temp = recipes.copy()
    for name, info in temp.items():
        if "School" in info:
            if info["School"] != school:
                recipes.pop(name)

    # Remove recipes unobtainable for the selected faction
    temp = recipes.copy()
    for name, info in temp.items():
        if "Faction" in info:
            if info["Faction"] != faction and info["Faction"] != "Any":
                recipes.pop(name)

    
    # Return dictionary with all relevant recipes
    return recipes

def prettyPrintPrice(price):
    gold = math.floor(price/10000)
    silver = math.floor(price%10000/100)
    copper = price%100

    result = ''
    if not gold:
        if not silver:
            result = "{}c".format(copper)
        else:
            result = "{}s{:02}c".format(silver, copper)
    else:
        result = "{}g{:02}s{:02}c".format(gold, silver, copper)
    
    return result

def sumPretty(prices):
    sum = 0
    for item in prices:
        item = item.translate({ord(i): None for i in 'gsc'})
        sum += int(item)

    return prettyPrintPrice(sum)