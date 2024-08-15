#!python3
# -*- coding: utf-8 -*-

from glob import glob
from os.path import basename
import xml.etree.ElementTree as ET


def xml_pre():
    print('<svg xmlns="http://www.w3.org/2000/svg" style="display: none;">')


def xml_post():
    print("</svg>")


def process(filename, xml):
    id = basename(filename).lower().split(".")[0]
    view_box = xml.attrib.get("viewBox", "0 0 40 40")
    print('  <symbol id="icon-{}" viewBox="{}">'.format(id, view_box))
    for child in xml:
        tag = child.tag.split("}")[1]
        if tag not in ("path", "circle", "rect", "g"):
            # print("to do: " + tag)
            continue
        print("    <{}".format(tag), end="")
        for k, v in child.attrib.items():
            print(' {}="{}"'.format(k, v), end="")
        print("/>")
    print("  </symbol>")


if __name__ == "__main__":
    svg_paths = [
        "src/website/svg/*.svg",
    ]

    xml_pre()
    for svg_path in svg_paths:
        svg_files = glob(svg_path)
        for svg_file in svg_files:
            with open(svg_file, "r") as fd:
                lines = fd.read()
                xml = ET.fromstring(lines)
                process(svg_file, xml)
    xml_post()
