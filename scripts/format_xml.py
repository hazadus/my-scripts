#!/usr/bin/env -S uv run --quiet --script
"""
Форматирует XML-файл с описанием RSS-лент
"""

from xml.dom import minidom

FILE_PATH = "feeds.opml"

with open(FILE_PATH, "r", encoding="utf-8") as f:
    xml = f.read()

dom = minidom.parseString(xml)
pretty_xml = dom.toprettyxml(indent="  ")

with open(FILE_PATH, "w", encoding="utf-8") as f:
    f.write(pretty_xml)
