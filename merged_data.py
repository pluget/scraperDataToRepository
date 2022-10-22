import os
import json
import base64
import random
import requests
import re
import pathlib
from io import BytesIO
from dotenv import load_dotenv
from unidecode import unidecode
from urllib.parse import urlencode
import webbrowser
import nft_storage
from nft_storage.api import nft_storage_api


def main():
    load_dotenv()
    CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID")
    CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET")

    NFT_STORAGE_API_KEY = os.environ.get("NFT_STORAGE_API_KEY")

    params = {"client_id": CLIENT_ID, "scope": "user"}

    endpoint = "https://github.com/login/oauth/authorize"
    endpoint = endpoint + "?" + urlencode(params)
    print(endpoint)
    webbrowser.open(endpoint)

    # Open the matches file
    f = open("../scraperRepository/matches.json", "r")
    # Read the file
    data = json.load(f)
    # Close the file
    f.close()

    # Open the spigot file
    f = open("../scraperRepository/spigetResources.json", "r")
    # Read the file
    spigot_data = json.load(f)
    # Close the file
    f.close()

    # Open the spigot versions file
    f = open("../scraperRepository/spigetVersions.json", "r")
    # Read the file
    spigot_versions_data = json.load(f)
    # Close the file
    f.close()

    # Open the version to cid file
    f = open("../../mpmgg/repository/verid.json", "r")
    # Read the file
    vertocid_data = json.load(f)
    # Close the file
    f.close()

    code = input()

    params = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
    }
    endpoint = "https://github.com/login/oauth/access_token"
    response = requests.post(
        endpoint, params=params, headers={"Accept": "application/json"}
    ).json()
    access_token = response["access_token"]

    session = requests.session()
    session.headers = {"Authorization": f"token {access_token}"}

    config_nfts = nft_storage.Configuration(access_token=NFT_STORAGE_API_KEY)

    api_nfts = nft_storage_api.NFTStorageAPI(nft_storage.ApiClient(config_nfts))

    for plugin in data:
        # Create simplified version of the plugin name
        plugin_name = "-".join(
            filter(
                None,
                re.split(
                    r" +",
                    unidecode(re.sub(r"[^a-zA-Z0-9 ]", "", plugin[2]["name"])).lower(),
                ),
            )
        )

        print("Starting with " + plugin_name)

        plugin_name_letter = ""
        if len(plugin_name) > 0:
            plugin_name_letter = plugin_name[0]
        else:
            plugin_name_letter = (
                "?"  # If the plugin name is empty, use ? as the first letter
            )
            plugin_name = "unknown" + str(
                random.randrange(0, 2137420)
            )  # Use unknown with random number as the name

        # If the plugin already exists, skip it
        if os.path.exists("../repository/" + plugin_name[0] + "/" + plugin_name):
            continue

        # Create the directory for the plugin
        pathlib.Path("../repository/" + plugin_name[0] + "/" + plugin_name).mkdir(
            parents=True, exist_ok=True
        )

        # Get the source link
        source_link = ""
        if (
            "sourceCodeLink" in plugin[2]
            and len(plugin[2]["sourceCodeLink"].split("/")) > 4
        ):
            source_link = plugin[2]["sourceCodeLink"]
        elif "source" in plugin[1] and len(plugin[1]["source"].split("/")) > 4:
            source_link = plugin[1]["source"]

        source_link_splitted = source_link.split("/")

        # Get the license, archival status and the github data
        spdx = ""
        archived = False
        github_data = {}

        if len(source_link_splitted) > 4 and source_link_splitted[2] == "github.com":
            github_data = {
                "type": "github",
                "url": source_link,
                "authors": [],
                "releasesPageUrl": source_link + "/releases",
            }

            github_json = session.get(
                "https://api.github.com/repos/"
                + source_link_splitted[3]
                + "/"
                + source_link_splitted[4].split(".")[0]
            ).json()

            if "stargazers_count" in github_json:
                github_data["numberOfStars"] = github_json["stargazers_count"]
            if "license" in github_json and github_json["license"] is not None:
                spdx = github_json["license"]["spdx_id"]

            if "archived" in github_json:
                archived = github_json["archived"]
                github_data["archived"] = archived

            github_contributors_json = session.get(
                "https://api.github.com/repos/"
                + source_link_splitted[3]
                + "/"
                + source_link_splitted[4].split(".")[0]
                + "/contributors"
            ).json()
            if (
                github_contributors_json is not None
                and "message" not in github_contributors_json
            ):
                for contributor in github_contributors_json:
                    github_data["authors"].append(contributor["login"])

        # If depricated in Bukkit mark as archived
        if plugin[1]["depricated"] is True:
            archived = True

        # Get the icon from Bukkit and upload to NFT Storage
        bukkit_icon = ""
        if "iconUrl" in plugin[1]:
            bukkit_icon = plugin[1]["iconUrl"]

        bukkit_icon_blob = BytesIO()
        if bukkit_icon != "":
            bukkit_icon_blob = BytesIO(requests.get(bukkit_icon).content)

        cid_bukkit_icon = ""
        if bukkit_icon_blob.getbuffer().nbytes > 0:
            api_nfts_response = api_nfts.store(
                bukkit_icon_blob, _check_return_type=False
            )
            cid_bukkit_icon = api_nfts_response["value"]["cid"]

        # Get the spigot icon url and upload image to NFT Storage
        plugin_spigot = list(filter(lambda x: x["id"] == plugin[2]["id"], spigot_data))[
            0
        ]
        spigot_icon = ""
        spigot_icon_blob = BytesIO()
        if plugin_spigot is not None and "icon" in plugin_spigot:
            if "url" in plugin_spigot["icon"] and plugin_spigot["icon"]["url"] != "":
                spigot_icon = "https://spigotmc.org/" + plugin_spigot["icon"]["url"]
            if "data" in plugin_spigot["icon"] and plugin_spigot["icon"]["data"] != "":
                spigot_icon_blob = BytesIO(
                    base64.b64decode(plugin_spigot["icon"]["data"])
                )

        cid_spigot_icon = ""
        if spigot_icon_blob.getbuffer().nbytes > 0:
            api_nfts_response = api_nfts.store(
                spigot_icon_blob, _check_return_type=False
            )
            cid_spigot_icon = api_nfts_response["value"]["cid"]

        # Create array of Spigot authors
        spigot_authors = []
        if "contributors" in plugin[2]:
            spigot_authors = plugin[2]["contributors"].split(", ")

        # Create dictionary of plugin data
        plugin_data = {
            "name": plugin[2]["name"],
            "icon": cid_bukkit_icon,
            "license": spdx,
            "archived": archived,
            "gitUrl": source_link,
            "description": plugin[2]["tag"],
            "releaseDate": plugin[2]["releaseDate"],
            "updateDate": plugin[2]["updateDate"],
            "data": [
                {
                    "id": plugin[2]["id"],
                    "type": "spigot",
                    "url": "https://spigotmc.org/resources/" + str(plugin[2]["id"]),
                    "name": plugin[2]["name"],
                    "description": plugin[2]["tag"],
                    "archived": False,
                    "authors": spigot_authors,
                    "icon": cid_spigot_icon,
                    "iconUrl": spigot_icon,
                    "numberOfDownloads": plugin[2]["downloads"],
                    "rating": plugin[2]["rating"]["average"],
                    "numberOfVotes": plugin[2]["rating"]["count"],
                    "releasesPageUrl": "https://spigotmc.org/resources/"
                    + str(plugin[2]["id"])
                    + "/releases",
                },
                {
                    "id": plugin[1]["id"],
                    "type": "bukkit",
                    "url": plugin[1]["url"],
                    "name": plugin[1]["title"],
                    "description": plugin[1]["desc"],
                    "archived": plugin[1]["depricated"],
                    "authors": plugin[1]["authors"],
                    "icon": cid_bukkit_icon,
                    "iconUrl": bukkit_icon,
                    "numberOfDownloads": plugin[1]["downloads"],
                    "releasesPageUrl": plugin[1]["url"] + "/files",
                },
            ],
        }

        # If the plugin is on github
        if github_data != {}:
            plugin_data["data"].append(github_data)

        # Create the array of dictionaries of version data
        versions_data = []
        spigot_versions_object = list(
            filter(lambda x: x["id"] == plugin[2]["id"], spigot_versions_data)
        )[0]
        spigot_versions = list()
        if "versions" in spigot_versions_object:
            spigot_versions = spigot_versions_object["versions"]

        for version in spigot_versions:
            version_cid = ""
            if (
                version["id"] in vertocid_data
                and vertocid_data[version["id"]] is not None
            ):
                version_cid = vertocid_data[version["id"]]

            versions_data.append(
                [
                    version["name"],
                    {
                        "about": [
                            {
                                "type": "spigot",
                                "sourceUrl": "https://spigotmc.org/resources/"
                                + str(plugin[2]["id"])
                                + "/history",
                                "downloadUrl": "https://www.spigotmc.org/resources/"
                                + str(plugin[2]["id"])
                                + "/download?version="
                                + str(version["id"]),
                                "numberOfDownloads": version["downloads"],
                                "rating": version["rating"]["average"],
                                "numberOfVotes": version["rating"]["count"],
                                "releaseDate": version["releaseDate"],
                            }
                        ],
                        "cid": version_cid,
                        "releaseDate": version["releaseDate"],
                        "supportedApis": ["paper", "spigot", "bukkit"],
                        "dependencies": [],
                        "optionalDependencies": [],
                        "supportedVersions": plugin[2]["testedVersions"],
                    },
                ]
            )

            # Put plugin data into the repository
            f = open(
                "../repository/"
                + plugin_name[0]
                + "/"
                + plugin_name
                + "/"
                + "data.json",
                "w+",
            )
            f.write(json.dumps(plugin_data))
            f.close()

            # Put version data into the repository
            for version in versions_data:
                f = open(
                    "../repository/"
                    + plugin_name[0]
                    + "/"
                    + plugin_name
                    + "/"
                    + version[0]
                    + ".json",
                    "w+",
                )
                f.write(json.dumps(version[1]))
                f.close()

        print("Done with " + plugin_name)


if __name__ == "__main__":
    main()
