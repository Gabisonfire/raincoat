import requests


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
        r = requests.get(torrent.download, allow_redirects=False)
        if r.status_code == 302:
            return r.headers['Location']
        else:
            print(f"Unexpected return code: {r.status_code}")
    except Exception as e:
        print(f"Could not fetch torrent url: {str(e)}")
        exit()

