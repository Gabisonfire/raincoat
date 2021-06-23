# Raincoat

Raincoat is a CLI tool to search torrents using [Jackett](https://github.com/Jackett/Jackett)'s indexers and send them directly to your client.

### Installation

`pip install raincoat-jackett`

### Requirements

- Python 3.6+
- Jackett and configured indexers
- qBittorrent, Transmission or Deluge (or use local download option)
- libtorrent if you use local downloader and magnet links.
  - Arch: `pacman -S libtorrent-rasterbar`
  - Ubuntu: `apt-get install python-libtorrent -y`
  - Fedora: `dnf install rb_libtorrent-python2`

### Usage

`raincoat "Terms to search"`

#### Parameters

- -k, --key
  - Specify a Jackett API key
- -l, --length
  - Max number of characters displayed in the "Description" column.
- -L, --limit
  - Limits the number of results displayed.
- -c, --config
  - Specifies a different config path.
- -s, --sort
  - Change the sorting criteria. Valid choices are: 'seeders', 'leechers', 'ratio', 'size' and 'description'. Default/not specified is 'seeders'.
- -i, --indexer
  - Change the indexer used for your search, in cases where you want to only search one site. Default is "all".
- -d, --download x
  - Grab the first x resultd and send to the client immediately. Defaults to 1.
- -K, --insecure
  - Don't verify certificates  
- --local
  - Force use of "local" file download.
- --list
  - Specify a file to load search terms from. One term per line.
- --verbose
  - Extra verbose logging sent to log file.

#### Configuration file

Upon installation, a config file is created in your home directory. Before you can use Raincoat, you will need to modify it.

```json
{
  "jackett_apikey": "",
  "jackett_url": "http://your_base_jackett_url",
  "jackett_indexer": "all",
  "description_length": 100,
  "exclude": "words to exclude",
  "results_limit": 20,
  "client_url": "http://your_torrent_client_api",
  "display": "grid",
  "torrent_client": "qbittorrent",
  "torrent_client_username": "admin",
  "torrent_client_password": "admin",
  "download_dir": "/some/directory/"
}
```

- jackett_apikey (string)
  - The api key provided by Jackett, found on the dashboard.
- jackett_url (string)
  - The base url for your jackett instance. (default: http://127.0.0.1:9117)
- jackett_indexer (string)
  - The jackett indexer you wish to use for searches.
- description_length (int)
  - The default description length
- exclude (string)
  - Words to exclude from your results seperated by a space.
- results_limit (int)
  - Max number of lines to show.
- client_url (string)
  - The url to your torrent client's API
- display (string)
  - The display style of the results table. You can view available choices [here](https://pypi.org/project/tabulate/)
- torrent_client (string)
  - Your torrent client. Valid options are: local, qbittorrent, transmission and deluge.
- torrent_client_username (string)
  - Your torrent client's login username.
- torrent_client_password
  - Your torrent client's login password. Note: Only Transmission accepts empty passwords.
- download_dir
  - Where to save the torrent files when using "local" downloader.

# Built with

- requests
- justlog
- colorama
- tabulate
- transmission-clutch
- deluge-client
- python-qbittorrent

All available on Pypi.

# License

This project is licensed under the MIT License
