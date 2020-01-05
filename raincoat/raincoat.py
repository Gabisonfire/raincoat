import argparse
import colorama
import requests
import justlog
import json
import os
from .helpers import greet, get_torrent_by_id, fetch_torrent_url
from tabulate import tabulate
from .torrent import torrent, filter_out, transmission, deluge, qbittorrent
from justlog import justlog, settings
from justlog.classes import Severity, Output, Format
from .config import load_config
from pathlib import Path


# Constants
VERSION = "0.5"
APP_NAME = "Raincoat"

parser = argparse.ArgumentParser()
parser.add_argument("search", help="The field to search.")
parser.add_argument("-k", "--key", help="The Jackett API key.")
parser.add_argument("-l", "--length", help="Max results description length.", type=int)
parser.add_argument("-L", "--limit", help="Max number of results.", type=int)
parser.add_argument("-c", "--config", help="Specify a different config file path.")
parser.add_argument("-s", "--sort", help="Change sorting criteria.", action="store", dest="sort", choices=['seeders', 'leechers', 'ratio', 'size', 'description'])
parser.add_argument("-i", "--indexer", help="The Jackett indexer to use for your search.")
args = parser.parse_args()

# Use default path for the config file and load it initially
cfg_path = f"{str(Path.home())}/.config/{APP_NAME}.json"
if args.config is not None:
    cfg_path = args.config
cfg = load_config(cfg_path)


# Setup logger
logger = justlog.Logger(settings.Settings())
logger.settings.colorized_logs = True
logger.settings.log_output = [Output.FILE]
logger.settings.log_format = Format.TEXT
logger.settings.log_file = f"{str(Path.home())}/.config/{APP_NAME}.log"
logger.settings.update_field("timestamp", "$TIMESTAMP")
logger.settings.update_field("level", "$CURRENT_LOG_LEVEL")
logger.settings.string_format = "[ $timestamp ] :: $CURRENT_LOG_LEVEL :: $message"

logger.debug(f"{APP_NAME} v{VERSION}")
greet(VERSION)


# Globals
torrents = []
APIKEY = cfg['jackett_apikey']
JACKETT_URL = cfg['jackett_url']
JACKETT_INDEXER = cfg['jackett_indexer']
DESC_LENGTH = cfg['description_length']
EXCLUDE = cfg['exclude']
RESULTS_LIMIT = cfg['results_limit']
CLIENT_URL = cfg['client_url']
DISPLAY = cfg['display']
TOR_CLIENT = cfg['torrent_client']
TOR_CLIENT_USER = cfg['torrent_client_username']
TOR_CLIENT_PW = cfg['torrent_client_password']

def set_overrides():
    if args.key is not None:
        global APIKEY
        APIKEY = args.key       

    if args.length is not None:
        global DESC_LENGTH
        DESC_LENGTH = args.length

    if args.limit is not None:
        global RESULTS_LIMIT
        RESULTS_LIMIT = args.limit

    if args.indexer is not None:
        global JACKETT_INDEXER
        JACKETT_INDEXER = args.key

    # Set default sorting
    if args.sort is None:
        args.sort = "seeders"

def prompt_torrent():
    print("\nCommands: \n\t:download, :d ID\n\t:quit, :q\n\tTo search something else, just type it and press enter.")
    try:
        cmd = input("-> ")
    except Exception as e:
        print(f"Invalid input: {str(e)}")
        prompt_torrent()
    if cmd.startswith(":download") or cmd.startswith(":d"):
        id = cmd.split()[1]
        if not id.isdigit():
            print(f"Not a valid id.({id})")
            logger.warning(f"Not a valid id.({id}). We were expecting an integer.")
            prompt_torrent()
        else:
            download(id)
            exit()
    if cmd.startswith(":quit") or cmd.startswith(":q"):
        exit()
    if cmd.strip() == "":
        prompt_torrent()
    search(cmd)

def download(id):
    torrent = get_torrent_by_id(torrents, id)
    if torrent is None:
        print(f"Cannot find {id}.")
        logger.warning(f"Invalid id. The ID provided was not found in the list.")
        search(args.search)    
    else:
        if TOR_CLIENT.lower() == "transmission":
            transmission(torrent, CLIENT_URL, TOR_CLIENT_USER, TOR_CLIENT_PW, logger)
        elif TOR_CLIENT.lower() == "deluge":
            deluge(torrent, CLIENT_URL, TOR_CLIENT_USER, TOR_CLIENT_PW, logger)
        elif TOR_CLIENT.lower() == "qbittorrent":
            qbittorrent(torrent, CLIENT_URL, TOR_CLIENT_USER, TOR_CLIENT_PW, logger)
        else:
            print(f"Unsupported torrent client. ({TOR_CLIENT})")
            exit()


def search(search_terms):
    print(f"Searching for \"{search_terms}\"...\n")
    try:
        r = requests.get(f"{JACKETT_URL}/api/v2.0/indexers/{JACKETT_INDEXER}/results?apikey={APIKEY}&Query={search_terms}")
        if r.status_code != 200:
            print(f"The request to Jackett failed. ({r.status_code})")
            logger.error(f"The request to Jackett failed. ({r.status_code}) :: {JACKETT_URL}api?passkey={APIKEY}&search={search_terms}")
            exit()
        res = json.loads(r.content)        
    except Exception as e:
        print(f"The request to Jackett failed.")
        logger.error(f"The request to Jackett failed. {str(e)}")
        exit()
    id = 1
    global torrents
    torrents = []
    display_table = []
    for r in res['Results']:
        if filter_out(r['Title'], EXCLUDE):
            continue
        if len(r['Title']) > DESC_LENGTH:
            r['Title'] = r['Title'][0:DESC_LENGTH]
        download_url = r['MagnetUri'] if r['MagnetUri'] else r['Link']
        torrents.append(torrent(id, r['Title'].encode(
            'ascii', errors='ignore'), r['CategoryDesc'], r['Seeders'], r['Peers'], download_url, r['Size']))
        id += 1    

    # Sort torrents array
    sort_torrents(torrents)

    count = 1
    for tor in torrents:
        if count > RESULTS_LIMIT:
            break
        display_table.append([tor.id, tor.description, tor.media_type,
                              tor.size, tor.seeders, tor.leechers, tor.ratio])
        count += 1
    print(tabulate(display_table, headers=[    
          "ID", "Description", "Type", "Size (GB)", "Seeders", "Leechers", "Ratio"], floatfmt=".2f", tablefmt=DISPLAY))
    print(f"\nShowing {count -1} of {len(torrents)}, limit is set to {RESULTS_LIMIT}")
    prompt_torrent()

def sort_torrents(torrents):
    if args.sort == "seeders":
        return torrents.sort(key=lambda x: x.seeders, reverse=True)
    if args.sort == "leechers":
        return torrents.sort(key=lambda x: x.leechers, reverse=True)        
    if args.sort == "size":
        return torrents.sort(key=lambda x: x.size, reverse=True)
    if args.sort == "ratio":
        return torrents.sort(key=lambda x: x.ratio, reverse=True)
    if args.sort == "description":
        return torrents.sort(key=lambda x: x.description, reverse=True)

def main():
    set_overrides()
    search(args.search)
