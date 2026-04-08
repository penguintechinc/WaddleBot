"""
Default Profanity Word List

A curated list of common English profanity terms for opt-in content filtering.
Communities enable this via the 'use_default_profanity_list' config toggle.
These words are merged with the community's custom blocked_words at check time.

Matching is case-insensitive substring matching (consistent with existing filter logic).
"""
from typing import List

# -- Vulgarities & strong language --
_VULGARITIES: List[str] = [
    "fuck", "fucker", "fuckers", "fucking", "fucked", "fucks",
    "motherfucker", "motherfuckers", "motherfucking",
    "shit", "shits", "shitty", "shitting", "bullshit", "horseshit",
    "ass", "asshole", "assholes", "asses", "jackass", "dumbass", "badass",
    "damn", "damned", "damnit", "goddamn", "goddamnit",
    "hell", "bitch", "bitches", "bitchy", "bitching",
    "bastard", "bastards",
    "crap", "crappy",
    "dick", "dicks", "dickhead", "dickheads",
    "cock", "cocks", "cocksucker", "cocksuckers",
    "piss", "pissed", "pissing",
    "cunt", "cunts",
    "twat", "twats",
    "wanker", "wankers", "wank",
    "bollocks",
    "arse", "arsehole",
    "tosser", "tossers",
    "prick", "pricks",
]

# -- Slurs & hate speech --
_SLURS: List[str] = [
    "nigger", "niggers", "nigga", "niggas",
    "faggot", "faggots", "fag", "fags",
    "dyke", "dykes",
    "tranny", "trannies",
    "retard", "retards", "retarded",
    "spic", "spics",
    "chink", "chinks",
    "kike", "kikes",
    "wetback", "wetbacks",
    "gook", "gooks",
    "beaner", "beaners",
    "coon", "coons",
    "raghead", "ragheads",
    "towelhead", "towelheads",
    "cracker", "crackers",
    "honky", "honkey",
    "whitetrash",
    "zipperhead",
]

# -- Sexual content --
_SEXUAL: List[str] = [
    "porn", "porno", "pornography",
    "hentai",
    "dildo", "dildos",
    "blowjob", "blowjobs",
    "handjob", "handjobs",
    "rimjob",
    "cumshot",
    "cum", "cumming",
    "jizz",
    "orgasm", "orgasms",
    "masturbate", "masturbating", "masturbation",
    "ejaculate", "ejaculation",
    "bukkake",
    "gangbang",
    "milf",
    "anal",
    "queef",
    "whore", "whores",
    "slut", "sluts", "slutty",
    "hooker", "hookers",
    "prostitute",
]

# -- Common leetspeak & evasion variants --
_LEETSPEAK: List[str] = [
    "f u c k", "f.u.c.k", "f_u_c_k",
    "s h i t", "s.h.i.t", "s_h_i_t",
    "b i t c h", "b.i.t.c.h",
    "fck", "fuk", "phuck", "phuk",
    "sh1t", "sht",
    "b1tch", "btch",
    "a$$", "a$$hole",
    "d1ck",
    "c0ck",
    "stfu", "gtfo",
    "n1gger", "n1gga",
    "f4g", "f4ggot",
    "r3tard", "r3tarded",
]

DEFAULT_PROFANITY_WORDS: List[str] = (
    _VULGARITIES + _SLURS + _SEXUAL + _LEETSPEAK
)
