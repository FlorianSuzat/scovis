import json
import math
import numpy as np
import os
from scipy.stats import bootstrap


def signif(x, digit):
    if x == 0:
        return 0
    return round(x, digit - int(math.floor(math.log10(abs(x)))) - 1)


def scoreGeoLvlObs(refFolder, testFolder):
    refXpName = refFolder.split("/")[-1]
    testXpName = testFolder.split("/")[-1]
    config = {
        "ref": {"xpname": refXpName, "folder": refFolder},
        "test": {"xpname": refXpName, "folder": testFolder},
    }

    metadataDict, globDict, results = initDicts(config)
    metadataDict["title"] = "Observation score {} vs {}".format(refFolder, testFolder)

    for refFile in os.listdir(refFolder):
        if not os.path.isfile("{}/{}".format(testFolder, refFile)):
            print("file {} not in test dir".format(refFile))
            continue  # only computer for dates presents in both

        # refFile must be YYYYMMDDHH_TT.json
        try:
            yyyymmddhh, term = refFile.replace(".json", "").split("_")
            term = int(term)

        except Exception as e:
            raise RuntimeError(
                "instants files must be named yyyymmddhh_tt.json, error for file {}, exeption is {}".format(
                    refFile, e
                )
            )

        # now read jsons
        data = {"ref": {}, "test": {}}
        try:
            with open("{}/{}".format(refFolder, refFile)) as f:
                data["ref"] = json.loads(f.read())
        except Exception as e:
            print("file {} is not valid json, exception is {}".format(refFile, e))
            continue
        try:
            with open("{}/{}".format(testFolder, refFile)) as f:
                data["test"] = json.loads(f.read())
        except Exception as e:
            print("file {} is not valid json, exception is {}".format(refFile, e))
            continue

        if term not in metadataDict["terms"]:
            metadataDict["terms"].append(term)
        if yyyymmddhh not in metadataDict["yyyymmddhh"]:
            metadataDict["yyyymmddhh"].append(yyyymmddhh)

        for sKey, rVals in data["ref"].items():
            if sKey == "message":
                continue
            isRadiance = "s_" in sKey and "_g_" in sKey
            isStdObs = ("_l_" in sKey and "_g_" in sKey) or (
                "_z_" in sKey and "_g_" in sKey
            )
            if not (isRadiance or isStdObs):
                continue
            try:
                tVals = data["test"][sKey]
            except Exception as e:
                print("key {} not in test json,{}".format(sKey, e))
                continue

            eTest = float(tVals["e"])
            eRef = float(rVals["e"])
            bTest = float(tVals["b"])
            bRef = float(rVals["b"])
            # nTest = float(tVals["n"])
            nRef = float(rVals["n"])
            if eRef == 0:
                continue
            buf = sKey.split("_")
            if "s_" in sKey and "_c_" not in sKey:
                continue  # we don't want s_ stats without chans
            if "s_" in sKey:
                varno_obstype = "s_" + buf[1]  # chanel
                lvl = buf[3]
                loc = buf[5]
            else:
                varno = buf[1]
                obstype = buf[3]
                lvl = buf[5]
                loc = buf[7]
                varno_obstype = "v_" + varno + "_o_" + obstype

            # sumup winds and skip solo wind
            if "s_" not in sKey and varno in ["3", "4", "41", "42", "124", "125"]:
                mixVarno = calcMixVarno(varno)
                varno_obstype = "v_" + mixVarno + "_o_" + obstype

            createKeysInDict(
                globDict,
                [varno_obstype, loc, lvl, term],
                {"b": [], "f": [], "n": [], "bt": [], "br": [], "e": []},
            )
            createKeysInDict(
                results,
                [varno_obstype, loc, lvl, term],
                {
                    "b": {"q": {}},
                    "n": {"q": {}},
                    "bt": {"q": {}},
                    "br": {"q": {}},
                    "f": {"q": {}},
                    "e": {"q": {}},
                },
            )
            globDict[varno_obstype][loc][lvl][term]["e"].append(
                100 * (eTest - eRef) / abs(eTest)
            )
            globDict[varno_obstype][loc][lvl][term]["f"].append(eTest - eRef)
            globDict[varno_obstype][loc][lvl][term]["n"].append(nRef)
            globDict[varno_obstype][loc][lvl][term]["b"].append(abs(bTest) - abs(bRef))
            globDict[varno_obstype][loc][lvl][term]["bt"].append(bTest)
            globDict[varno_obstype][loc][lvl][term]["br"].append(bRef)
            metadataDict["borns"].setdefault(varno_obstype, bornsInit())

    for varno_obstype, v1 in globDict.items():
        for loc, v2 in v1.items():
            for lvl, v3 in v2.items():
                for term, vList in v3.items():
                    n = len(vList["f"])
                    sqrn = np.sqrt(n)

                    for itm in ["b", "f", "n", "bt", "br", "e"]:
                        std = np.std(vList[itm])
                        mean = np.mean(vList[itm])
                        stdOverSqrn = std / sqrn
                        results[varno_obstype][loc][lvl][term][itm]["a"] = signif(
                            mean, 3
                        )
                        results[varno_obstype][loc][lvl][term][itm]["s"] = signif(
                            std, 3
                        )
                        results[varno_obstype][loc][lvl][term][itm]["w"] = signif(
                            stdOverSqrn, 3
                        )
                        results[varno_obstype][loc][lvl][term][itm]["n"] = n
                        del results[varno_obstype][loc][lvl][term][itm]["q"]
                        if (
                            itm != "n"
                            and results[varno_obstype][loc][lvl][term][itm]["a"] != 0
                        ):
                            fillBorns(
                                metadataDict["borns"][varno_obstype][itm],
                                results[varno_obstype][loc][lvl][term][itm]["a"],
                            )
                    for itm in ["b", "e"]:
                        results[varno_obstype][loc][lvl][term][itm]["c"] = (
                            bootstrapTest(vList[itm])
                        )
                    print(varno_obstype, loc, lvl, term, "done!")

    metadataDict["terms"].sort()
    scoreName = "{}vs{}".format(testXpName, refXpName)
    with open("scores/{}.json".format(scoreName), "w") as f:
        f.write(json.dumps({"data": results, "metadata": metadataDict}))
    print("file {} written in scores directory".format(scoreName))


def calcMixVarno(varno):
    if varno in ["3", "4"]:
        return "901"
    elif varno in ["41", "42"]:
        return "902"
    elif varno in ["124", "125"]:
        return "901"


def bornsInit():
    return {
        "b": {"min": 999999999, "max": -999999999, "absMax": -99999999},
        "e": {"min": 999999999, "max": -999999999, "absMax": -99999999},
        "bt": {"min": 999999999, "max": -999999999, "absMax": -99999999},
        "br": {"min": 999999999, "max": -999999999, "absMax": -99999999},
        "f": {"min": 999999999, "max": -999999999, "absMax": -99999999},
    }


def fillBorns(borns, val):
    if not hasattr(val, "split"):
        borns["max"] = max(val, borns["max"])
        borns["min"] = min(val, borns["min"])
        borns["absMax"] = max(abs(borns["max"]), abs(borns["min"]))


def bootstrapTest(serie):
    if len(serie) < 2:
        return 0
    data = (serie,)
    confidencesList = [0.95, 0.90, 0.667]
    boostrap_ci = None
    for confidence in confidencesList:
        if boostrap_ci is None:
            bootstrap_ci = bootstrap(
                data, np.mean, confidence_level=confidence, n_resamples=500
            )
        else:
            bootstrap_ci = bootstrap(
                data,
                np.mean,
                confidence_level=confidence,
                n_resamples=500,
                boostrap_result=boostrap_ci,
            )
        sign = 0
        if bootstrap_ci.confidence_interval.high < 0:
            # amelioration
            sign = -1
        elif bootstrap_ci.confidence_interval.low > 0:
            # degradation
            sign = 1

        if not sign == 0:
            break
    boostrapvalue = 0
    # for multiplicator
    # confidence=0.95  -> multiplicator must be 3
    # confidence=0.90  -> multiplicator must be 2
    # confidence=0.667 -> multiplicator must be 1
    multiplicator = 3 - confidencesList.index(confidence)
    if sign == 0:
        # all test have failed, not significative
        boostrapvalue = 0
    else:
        boostrapvalue = sign * multiplicator

    # boostrapvalue=-3 strong amelioration confidence 95%
    # boostrapvalue=-2  amelioration confidence 90%
    # boostrapvalue=-1  light amelioration confidence 65%
    # boostrapvalue=0  non signif
    # boostrapvalue=1  light degradation confidence 65%
    # boostrapvalue=2  degradation confidence 90%
    # boostrapvalue=3 strong degradation confidence 95%

    return boostrapvalue


def significativity(mean, stdOverSqrn):
    signifValue = 0  # default

    if mean < 0:
        if mean + (2.576 * stdOverSqrn) < 0:
            signifValue = -2  # strong benef
        elif mean + (1.96 * stdOverSqrn) < 0:
            signifValue = -1
    else:
        if mean - (2.576 * stdOverSqrn) > 0:
            signifValue = 2  # strong degradation
        elif mean - (1.96 * stdOverSqrn) > 0:
            signifValue = 1
    return signifValue


def sortAndSignifList(li):
    result = [signif(x, 3) for x in li]
    result.sort()
    return result


def qDictToSymbol(qDict):
    if qDict[0.995] < 0:
        return "++++"
    elif qDict[0.95] < 0:
        return "+++"
    elif qDict[0.8] < 0:
        return "++"
    elif qDict[0.5] < 0:
        return "+"
    elif qDict[0.5] > 0:
        return "-"
    elif qDict[0.2] > 0:
        return "--"
    elif qDict[0.05] > 0:
        return "---"
    elif qDict[0.005] > 0:
        return "----"
    else:
        return "?"


def initDicts(config):
    metadataDict = {
        "terms": [],
        "yyyymmddhh": [],
        "borns": {},
        "xpid": config,
    }
    globDict = {"ref": {}, "test": {}}
    results = {}
    return metadataDict, globDict, results


def createKeysInDict(d, keysList, last):
    if len(keysList) == 1:
        k = keysList.pop()
        if k not in d.keys():
            d[k] = last
    else:
        k = keysList[0]
        if k not in d.keys():
            d.setdefault(k, {})
        createKeysInDict(d[k], keysList[1:], last)


def isRadianceOrStdGeoLvlObs(sKey):
    isRadiance = "s_" in sKey and "_g_" in sKey
    isStdGeoLvlObs = ("_l_" in sKey and "_g_" in sKey) or (
        "_z_" in sKey and "_g_" in sKey
    )
    return isRadiance or isStdGeoLvlObs
