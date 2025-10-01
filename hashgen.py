"""
Generate hashes for trusted.json
"""
import json
import hashlib
import requests
from tqdm import tqdm
import re
def hash_string(s):
    """Generate SHA256 hash for a given string."""
    return hashlib.sha256(s.encode('utf-8')).hexdigest()
with open("trusted.json") as f:
        trusted = json.load(f)
apps=trusted.get("apps", [])
hashes={}
for app in tqdm(apps):
    one_hash={
        "name":app["name"],
        "url_pattern":app["url_pattern"],
        "description":app["description"],
        "valid_versions":app["valid_versions"],
        "repo_url": app.get("repo_url", ""),
        "git_repo": app.get("git_repo", ""),
        "website": app.get("website", ""),
        "hashes":{}
        }
    if len(app["valid_versions"][0]) == 0:
        url=app["url_pattern"].replace("\\/", "/").replace("\\.", ".").replace("\\\\","\\")
        try:
            r=requests.get(url)
            one_hash["hashes"][""]=hash_string(r.text)
        except requests.exceptions.RequestException as e:
            print(f"ERROR App {app['name']} request failed: {e}, url: {url}")
            continue
    else:
        for i in app["valid_versions"]:
            url_p=app["url_pattern"].replace("\\/", "/").replace("\\.", ".").replace("\\\\","\\")
            # Replace capturing groups with corresponding values from i
            url = url_p
            for j, replacement in enumerate(i):
                url = re.sub(r'\([^)]*\)', replacement, url, count=1)
                try:
                    r=requests.get(url)
                    one_hash["hashes"][",".join(i)] = hash_string(r.text)
                except requests.exceptions.RequestException as e:
                    print(f"ERROR App {app['name']} with version {i} request failed: {e}, url: {url}")
                    continue
    hashes[app["name"]]=one_hash
with open("hashes.json", "w") as f:
    json.dump(hashes, f, indent=4)