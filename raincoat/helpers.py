import requests
import os.path as pt
import shutil
import tempfile
import sys
import json
from raincoat import shared as shared
from justlog import justlog, settings
from justlog.classes import Severity, Output, Format
from pathlib import Path
from time import sleep
from urllib3.exceptions import InsecureRequestWarning

# Setup logger
logger = justlog.Logger(settings.Settings())
logger.settings.colorized_logs = True
logger.settings.log_output = [Output.FILE]
logger.settings.log_format = Format.TEXT
logger.settings.log_file = f"{str(Path.home())}/.config/Raincoat.log"
logger.settings.update_field("timestamp", "$TIMESTAMP")
logger.settings.update_field("level", "$CURRENT_LOG_LEVEL")
logger.settings.string_format = "[ $timestamp ] :: $CURRENT_LOG_LEVEL :: $message"

def greet(VERSION):
    print(r"")
    print(r", // ,,/ ,.// ,/ ,// / /, // ,/, /, // ,/,, // ,,/ ,./")
    print(r"_/_/,/,_,_/, /, /,.__,/,,/ ,.// ,/ ,// / /, // ,__ , /")
    print(r"\______   \_,_/_  |__| ,_,_,/,_/,_  _,,/, //_,_/  |_/,")
    print(r",|       _/\__  \ |  |/    \_/ ___\/  _ \__  \\   __\ ")
    print(r"/|    |   \ / __ \|  |   |  \  \__(  <_> ) __ \|  |,,/")
    print(r",|____|_  /(____  /__|___|  /\___  >____(____  /__|, ,")
    print(rf",/ ,,/,/\/,,/, ,\/ ,// , /\/,/ ,,\/, ,, // /,\/ {VERSION}")
    print(r", // ,/,// ,/ ,, ,/, // ,/ /,// ,/ ,// ,/ ,, /,//, /,/")
    print("")


def get_torrent_by_id(torrents, tid):
    for torrent in torrents:
        if torrent.id == int(tid):
            return torrent
    return None

def fetch_torrent_url(torrent):
    try:
        if shared.VERIFY:
            requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
        r = requests.get(torrent.download, allow_redirects=False, verify=shared.VERIFY)
        logger.debug(f"Requesting {torrent.download}")
        logger.debug(f"{str(r.status_code)}: {r.reason}")
        logger.debug(f"Headers: {json.dumps(dict(r.request.headers))}")
        if shared.VERBOSE_MODE:
            logger.debug(f"Content: {r.content}")

        if r.status_code == 302:
            if r.headers['Location'] is not None:
                return r.headers['Location']
            else:
                logger.error(f"Bad headers in torrent: ({r.headers})")
        elif r.status_code == 200:
            return torrent.download
        else:
            logger.error(f"Unexpected return code: {r.status_code}")
    except Exception as e:
        logger.error(f"Could not fetch torrent url: {str(e)}")
        if shared.VERBOSE_MODE:
            logger.debug(f"Torrent: {torrent}")
        exit()

def convert_to_torrent(url, save_path):
    # Importing here to prevent unneeded dependecies
    import libtorrent as lt

    if not pt.isdir(save_path):
        print(f"Invalid output folder: {save_path}")
        sys.exit(0)

    tempdir = tempfile.mkdtemp()
    ses = lt.session()
    params = {
        'save_path': tempdir,
        'storage_mode': lt.storage_mode_t(2),
        'url': url
    }
    handle = ses.add_torrent(params)

    print("Downloading Metadata (this may take a while)")
    while (not handle.has_metadata()):
        try:
            sleep(1)
        except KeyboardInterrupt:
            print("Aborting...")
            ses.pause()
            print("Cleanup dir " + tempdir)
            shutil.rmtree(tempdir)
            sys.exit(0)
    ses.pause()

    torinfo = handle.get_torrent_info()
    torfile = lt.create_torrent(torinfo)

    output = pt.abspath(torinfo.name() + ".torrent")
    output = pt.abspath(pt.join(save_path, torinfo.name() + ".torrent"))

    print(F"Saving torrent file to: {output}...")
    f = open(output, "wb")
    f.write(lt.bencode(torfile.generate()))
    f.close()
    print("Cleaning up temp files...")
    ses.remove_torrent(handle)
    shutil.rmtree(tempdir)
