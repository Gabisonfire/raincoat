import argparse
import colorama
import requests
import justlog
import json
import os
from raincoat import shared
from .helpers import greet, get_torrent_by_id, fetch_torrent_url
from tabulate import tabulate
from .torrent import torrent, filter_out, transmission, deluge, qbittorrent, local
from justlog import justlog, settings
from justlog.classes import Severity, Output, Format
from .config import load_config
from pathlib import Path
from urllib3.exceptions import InsecureRequestWarning

parser = argparse.ArgumentParser()
parser.add_argument("search", help="What to search for.", nargs='?')
parser.add_argument("-k", "--key", help="The Jackett API key.")
parser.add_argument("--list", help="Path to a file of terms to search.", type=str)
parser.add_argument("-l", "--length", help="Max results description length.", type=int)
parser.add_argument("-L", "--limit", help="Max number of results.", type=int)
parser.add_argument("-c", "--config", help="Specify a different config file path.")
parser.add_argument("-s", "--sort", help="Change sorting criteria.", action="store", dest="sort", choices=['seeders', 'leechers', 'ratio', 'size', 'description'])
parser.add_argument("-i", "--indexer", help="The Jackett indexer to use for your search.")
parser.add_argument("-d", "--download", help="Download and send the top 'x' results (defaults to 1) to the client and exit.", nargs='?', const=1, type=int)
parser.add_argument("-K", "--insecure", help="Enables to use self-signed certificates.", action="store_true")
parser.add_argument("--local", help="Override torrent provider with local download.", action="store_true")
parser.add_argument("--verbose", help="Very verbose output to logs.", action="store_true")
args = parser.parse_args()

shared.init()

# Use default path for the config file and load it initially
cfg_path = f"{str(Path.home())}/.config/{shared.APP_NAME}.json"
if args.config is not None:
    cfg_path = args.config
cfg = load_config(cfg_path)

shared.TORRENTS = []
shared.APIKEY = cfg['jackett_apikey']
shared.JACKETT_URL = cfg['jackett_url']
shared.JACKETT_INDEXER = cfg['jackett_indexer']
shared.DESC_LENGTH = cfg['description_length']
shared.EXCLUDE = cfg['exclude']
shared.RESULTS_LIMIT = cfg['results_limit']
shared.CLIENT_URL = cfg['client_url']
shared.DISPLAY = cfg['display']
shared.TOR_CLIENT = cfg['torrent_client']
shared.TOR_CLIENT_USER = cfg['torrent_client_username']
shared.TOR_CLIENT_PW = cfg['torrent_client_password']
shared.DOWNLOAD_DIR = cfg['download_dir']
shared.CURRENT_PAGE = 0


# Setup logger
logger = justlog.Logger(settings.Settings())
logger.settings.colorized_logs = True
logger.settings.log_output = [Output.FILE]
logger.settings.log_format = Format.TEXT
logger.settings.log_file = f"{str(Path.home())}/.config/{shared.APP_NAME}.log"
logger.settings.update_field("timestamp", "$TIMESTAMP")
logger.settings.update_field("level", "$CURRENT_LOG_LEVEL")
logger.settings.string_format = "[ $timestamp ] :: $CURRENT_LOG_LEVEL :: $message"

logger.debug(f"{shared.APP_NAME} v{shared.VERSION}")
greet(shared.VERSION)

def set_overrides():
    if args.key is not None:
        shared.APIKEY = args.key       

    if args.length is not None:        
        shared.DESC_LENGTH = args.length

    if args.limit is not None:        
        shared.RESULTS_LIMIT = args.limit

    if args.indexer is not None:        
        shared.JACKETT_INDEXER = args.indexer

    # Set default sorting
    if args.sort is None:
        args.sort = "seeders"

    if args.local:
        shared.TOR_CLIENT = "local"
    
    if args.verbose:
        shared.VERBOSE_MODE = True

    if args.download:
        shared.DOWNLOAD = args.download
    
    if args.insecure:
        requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
        shared.VERIFY = False

    if args.list:        
        if os.path.exists(args.list):
            shared.TERM_FILE = args.list
        else:
            print(f"{args.list} does not exist.")
            exit()

def prompt_torrent():
    if shared.DOWNLOAD:
        if len(shared.TORRENTS) > 0:
            # Prevent out of bound results
            if shared.DOWNLOAD > len(shared.TORRENTS):
                shared.DOWNLOAD = len(shared.TORRENTS)
            for i in range(shared.DOWNLOAD):
                download(shared.TORRENTS[i].id)
            if shared.TERM_FILE != None:
                return
            else:
                exit()
        else:
            print("Search did not yield any results.")
            exit()
    print("\nCommands: \n\t:download, :d ID\n\t:next, :n\n\t:prev, :p\n\t:quit, :q\n\tTo search something else, just type it and press enter.")
    try:
        cmd = input("-> ")
    except Exception as e:
        print(f"Invalid input: {str(e)}")
        prompt_torrent()
    if cmd.startswith(":download") or cmd.startswith(":d"):
        if len(cmd.split()) < 2:
            print("Invalid input")
            prompt_torrent()
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
    if cmd.startswith(":next") or cmd.startswith(":n"):
        display_results(shared.CURRENT_PAGE + 1)
    if cmd.startswith(":prev") or cmd.startswith(":p"):
        display_results(shared.CURRENT_PAGE - 1)        
    if cmd.strip() == "":
        prompt_torrent()
    search(cmd)

def download(id):
    torrent = get_torrent_by_id(shared.TORRENTS, id)
    if torrent is None:
        print(f"Cannot find {id}.")
        logger.warning(f"Invalid id. The ID provided was not found in the list.")
        search(args.search)    
    else:    
        if shared.TOR_CLIENT.lower() == "transmission":
            transmission(torrent, shared.CLIENT_URL, shared.TOR_CLIENT_USER, shared.TOR_CLIENT_PW, logger)
        elif shared.TOR_CLIENT.lower() == "deluge":
            deluge(torrent, shared.CLIENT_URL, shared.TOR_CLIENT_USER, shared.TOR_CLIENT_PW, logger)
        elif shared.TOR_CLIENT.lower() == "qbittorrent":
            qbittorrent(torrent, shared.CLIENT_URL, shared.TOR_CLIENT_USER, shared.TOR_CLIENT_PW, logger)
        elif shared.TOR_CLIENT.lower() == "local":
            local(torrent, shared.DOWNLOAD_DIR, logger)            
        else:
            print(f"Unsupported torrent client. ({shared.TOR_CLIENT})")
            exit()

def search(search_terms):
    print(f"Searching for \"{search_terms}\"...\n")
    try:
        url = f"{shared.JACKETT_URL}/api/v2.0/indexers/{shared.JACKETT_INDEXER}/results?apikey={shared.APIKEY}&Query={search_terms}"
        r = requests.get(url, verify=shared.VERIFY)
        logger.debug(f"Request made to: {url}")
        logger.debug(f"{str(r.status_code)}: {r.reason}")
        logger.debug(f"Headers: {json.dumps(dict(r.request.headers))}")
        if r.status_code != 200:
            print(f"The request to Jackett failed. ({r.status_code})")
            logger.error(f"The request to Jackett failed. ({r.status_code}) :: {shared.JACKETT_URL}api?passkey={shared.APIKEY}&search={search_terms}")
            exit()
        res = json.loads(r.content)
        res_count = len(res['Results'])
        logger.debug(f"Search yielded {str(res_count)} results.")
        if shared.VERBOSE_MODE:
            logger.debug(f"Search request content: {r.content}")
    except Exception as e:
        print(f"The request to Jackett failed.")
        logger.error(f"The request to Jackett failed. {str(e)}")
        exit()
    id = 1

    for r in res['Results']:
        if filter_out(r['Title'], shared.EXCLUDE):
            continue
        if len(r['Title']) > shared.DESC_LENGTH:
            r['Title'] = r['Title'][0:shared.DESC_LENGTH]
        download_url = r['MagnetUri'] if r['MagnetUri'] else r['Link']
        shared.TORRENTS.append(torrent(id, r['Title'].encode(
            'ascii', errors='ignore'), r['CategoryDesc'], r['Seeders'], r['Peers'], download_url, r['Size']))
        id += 1    

    # Sort torrents array
    sort_torrents(shared.TORRENTS)

    # Display results
    shared.CURRENT_PAGE = 1
    display_results(shared.CURRENT_PAGE)

def display_results(page):
    display_table = []
    if page < 1:
        prompt_torrent()    
    shared.CURRENT_PAGE = page
    count = 0
    slice_index = (shared.CURRENT_PAGE - 1) * shared.RESULTS_LIMIT
    for tor in shared.TORRENTS[slice_index:]:
        if count >= shared.RESULTS_LIMIT:
            break
        tor.size = "{:.2f}".format(float(tor.size)/1000000)
        display_table.append([tor.id, tor.description, tor.media_type,
                              f"{tor.size}GB", tor.seeders, tor.leechers, tor.ratio])
        count += 1
    print(tabulate(display_table, headers=[    
          "ID", "Description", "Type", "Size", "Seeders", "Leechers", "Ratio"], floatfmt=".2f", tablefmt=shared.DISPLAY))
    print(f"\nShowing page {shared.CURRENT_PAGE} - ({count * shared.CURRENT_PAGE} of {len(shared.TORRENTS)} results), limit is set to {shared.RESULTS_LIMIT}")    
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
    if shared.TERM_FILE is not None:
        f = open(shared.TERM_FILE, 'r')
        for line in f.readlines():
            search(line.strip())
        exit()
    elif not args.search:
        print("Nothing to search for.")
        exit()
    else:
        search(args.search)
