"""Curated site list for username enumeration.

Only sites whose public profile pages can be checked with an
unauthenticated GET request and which reliably return 404 (or a clear
missing-marker) for absent usernames. {u} is replaced by the username.

Confidence reflects how trustworthy a positive result is on that site:
some sites show soft-200 pages for missing profiles, so their hits
score lower until corroborated.
"""

SITES = [
    # developer
    {"name": "GitHub",        "url": "https://github.com/{u}",                 "confidence": 85},
    {"name": "GitLab",        "url": "https://gitlab.com/{u}",                 "confidence": 80},
    {"name": "Bitbucket",     "url": "https://bitbucket.org/{u}/",             "confidence": 75},
    {"name": "npm",           "url": "https://www.npmjs.com/~{u}",             "confidence": 80},
    {"name": "PyPI",          "url": "https://pypi.org/user/{u}/",             "confidence": 80},
    {"name": "Docker Hub",    "url": "https://hub.docker.com/u/{u}",           "confidence": 75},
    {"name": "Stack Overflow","url": "https://stackoverflow.com/users?tab=accounts&search={u}", "confidence": 40},
    {"name": "Dev.to",        "url": "https://dev.to/{u}",                     "confidence": 80},
    {"name": "Codepen",       "url": "https://codepen.io/{u}",                 "confidence": 75},
    {"name": "HackerRank",    "url": "https://www.hackerrank.com/profile/{u}", "confidence": 70},
    {"name": "Replit",        "url": "https://replit.com/@{u}",                "confidence": 75},
    {"name": "Kaggle",        "url": "https://www.kaggle.com/{u}",             "confidence": 80},
    # social / community
    {"name": "Reddit",        "url": "https://www.reddit.com/user/{u}/about.json", "confidence": 85, "json": True},
    {"name": "Mastodon",      "url": "https://mastodon.social/@{u}",           "confidence": 70},
    {"name": "Twitch",        "url": "https://m.twitch.tv/{u}",                "confidence": 55},
    {"name": "Pinterest",     "url": "https://www.pinterest.com/{u}/",         "confidence": 60},
    {"name": "Tumblr",        "url": "https://{u}.tumblr.com/",                "confidence": 70},
    {"name": "Flickr",        "url": "https://www.flickr.com/people/{u}",      "confidence": 75},
    {"name": "Vimeo",         "url": "https://vimeo.com/{u}",                  "confidence": 70},
    {"name": "SoundCloud",    "url": "https://soundcloud.com/{u}",             "confidence": 70},
    {"name": "Behance",       "url": "https://www.behance.net/{u}",            "confidence": 75},
    {"name": "Dribbble",      "url": "https://dribbble.com/{u}",               "confidence": 75},
    {"name": "Medium",        "url": "https://medium.com/@{u}",                "confidence": 70},
    {"name": "Substack",      "url": "https://{u}.substack.com/",              "confidence": 60},
    {"name": "Wattpad",       "url": "https://www.wattpad.com/user/{u}",       "confidence": 75},
    {"name": "Goodreads",     "url": "https://www.goodreads.com/{u}",          "confidence": 60},
    {"name": "Last.fm",       "url": "https://www.last.fm/user/{u}",           "confidence": 75},
    {"name": "Discogs",       "url": "https://www.discogs.com/user/{u}",       "confidence": 75},
    {"name": "Bandcamp",      "url": "https://bandcamp.com/{u}",               "confidence": 55},
    {"name": "Imgur",         "url": "https://imgur.com/user/{u}",             "confidence": 60},
    {"name": "Giphy",         "url": "https://giphy.com/channel/{u}",          "confidence": 65},
    {"name": "Slideshare",    "url": "https://www.slideshare.net/{u}",         "confidence": 65},
    {"name": "About.me",      "url": "https://about.me/{u}",                   "confidence": 75},
    {"name": "Gravatar",      "url": "https://en.gravatar.com/{u}",            "confidence": 75},
    {"name": "Keybase",       "url": "https://keybase.io/{u}",                 "confidence": 75},
    {"name": "Telegram",      "url": "https://t.me/{u}",                       "confidence": 55},
    {"name": "Steam",         "url": "https://steamcommunity.com/id/{u}",      "confidence": 70},
    {"name": "itch.io",       "url": "https://{u}.itch.io/",                   "confidence": 65},
    {"name": "Chess.com",     "url": "https://www.chess.com/member/{u}",       "confidence": 70},
    {"name": "Lichess",       "url": "https://lichess.org/@/{u}",              "confidence": 75},
    {"name": "Duolingo",      "url": "https://www.duolingo.com/profile/{u}",   "confidence": 55},
    {"name": "TryHackMe",     "url": "https://tryhackme.com/p/{u}",            "confidence": 70},
    {"name": "HackerOne",     "url": "https://hackerone.com/{u}",              "confidence": 75},
    {"name": "Bugcrowd",      "url": "https://bugcrowd.com/{u}",               "confidence": 70},
    {"name": "Patreon",       "url": "https://www.patreon.com/{u}",            "confidence": 55},
    {"name": "Ko-fi",         "url": "https://ko-fi.com/{u}",                  "confidence": 65},
    {"name": "Linktree",      "url": "https://linktr.ee/{u}",                  "confidence": 70},
]
