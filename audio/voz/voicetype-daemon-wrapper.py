#!/usr/bin/env python3
import os
import sys

os.chdir("/usr/lib")
sys.path.insert(0, "/usr/lib")
sys.path.insert(0, "/home/alpha/Playstoria/models/voz")
import punctuation_patch  # noqa: F401  (aplica o patch de pontuação)
from voicetype import voice_holdtospeak

voice_holdtospeak.main()
