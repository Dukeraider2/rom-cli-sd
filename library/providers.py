"""Translate user-selected sources to bounded single-file candidates."""
import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, urlencode, unquote, urlsplit
from .naming import basename
from .platforms import FORMATS
from .transfer import LIMIT


class Index(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links=[]
    def handle_starttag(self,tag,attrs):
        if tag=="a":
            href=dict(attrs).get("href")
            if href and len(self.links)<8192:
                self.links.append(href)


def candidate(provider, item, title, url, name, size=None, checksums=None, hint=None):
    basename(name)
    suffix=Path(name).suffix.lower()
    systems=[key for key,formats in FORMATS.items() if suffix in formats and (not hint or hint==key)]
    if not systems:
        return None
    if size is not None and not 0<int(size)<=LIMIT:
        return None
    sums={}
    for key,length in (("sha256",64),("sha1",40),("md5",32)):
        value=(checksums or {}).get(key)
        if value and isinstance(value,str) and re.fullmatch(f"[a-fA-F0-9]{{{length}}}",value):
            sums[key]=value.lower()
    identifier=hashlib.sha256((provider+"\n"+url).encode()).hexdigest()
    return dict(id=identifier,provider=provider,item=item,title=" ".join(str(title).split())[:200],
                name=name,url=url,systems=systems,size=int(size) if size is not None else None,checksums=sums)


def search(network,provider,query,system,page):
    if provider=="archive":
        # Each page is one Archive item; page through its supported files separately.
        words=" ".join(re.findall(r"[\w-]+",query))
        if not words:
            raise ValueError("enter a title")
        params=urlencode({"q":f'title:"{words}" AND (collection:homebrew OR collection:open_source_software OR collection:softwarelibrary_misc)',
                          "fl[]":"identifier","rows":1,"page":page,"output":"json","sort[]":"identifier asc"})
        result=json.loads(network.metadata(provider,"https://archive.org/advancedsearch.php?"+params))["response"]
        rows=[]
        for doc in result["docs"][:1]:
            item=doc["identifier"]
            if not isinstance(item,str) or not re.fullmatch(r"[\w-][\w.-]{0,99}",item,re.ASCII):
                raise ValueError("invalid source identifier")
            meta=json.loads(network.metadata(provider,"https://archive.org/metadata/"+item))
            for entry in meta["files"]:
                if not isinstance(entry,dict):
                    continue
                name=entry.get("name")
                try:
                    row=candidate(provider,item,meta["metadata"].get("title",item),
                                  "https://archive.org/download/"+item+"/"+quote(name,safe=""),name,
                                  entry.get("size"),entry,system)
                except (TypeError,ValueError,AttributeError):
                    continue
                if row:
                    rows.append(row)
        return rows, page<int(result["numFound"])
    if provider!="mirror" or not network.mirror:
        raise ValueError("configure a mirror in Desktop Mode first")
    def links(url):
        index=Index()
        index.feed(network.metadata(provider,url))
        return index.links
    base=network.mirror
    root=links(base)
    paths=[(base,root,None)]
    for key in ([system] if system else FORMATS):
        if key+"/" in root:
            paths.append((base+key+"/",links(base+key+"/"),key))
    rows={}
    for directory,entries,hint in paths:
        for href in entries:
            if any(ch in href for ch in "/?#:"):
                continue
            name=unquote(href)
            if query.casefold() not in name.casefold():
                continue
            try:
                row=candidate(provider,"Configured mirror",Path(name).stem,directory+quote(name,safe=""),
                              name,hint=hint or system)
            except ValueError:
                continue
            if row:
                rows[row["id"]]=row
    ordered=sorted(rows.values(),key=lambda row:(row["name"].casefold(),row["id"]))
    start=(page-1)*20
    return ordered[start:start+20],len(ordered)>start+20

